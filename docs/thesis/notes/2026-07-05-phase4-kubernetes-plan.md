# Phase 4: Cloud-Tier Elastic Scaling on Kubernetes — Implementation Plan

Date: 2026-07-05
Status: **planned, not implemented.** This document is the design/roadmap for
Phase 4. Implementation is deferred; the current thesis version (Phases 1–3)
will be tested and iterated first. Budget: ~3 months.

## 1. Goal and thesis claim

Deliver one *measured* result: the stateless cloud-tier LSTM-AE verifier,
deployed on Kubernetes, scales horizontally under a variable edge→cloud
escalation load, keeping verification latency bounded as the escalated stream
grows.

The claim is scoped to what a **local single-node cluster** (`kind`/`k3d`)
actually measures. It is *not* a claim about production multi-node edge
deployment, geographic distribution, or fault tolerance under real network
partitions — those remain future work (consistent with the simulator-only
honesty constraint used throughout the thesis). Only report numbers that were
observed; describe the manifests/architecture separately from the measured
scaling behaviour.

## 2. Why the cloud tier is the right scale target

- `cloud-tier` (`cloud/app/main.py`) is **stateless**: it holds only bounded
  in-memory counters/buffers, persists nothing, and reads the model artifact
  read-only. Replicas are independent — safe to scale horizontally.
- It already exposes `/health` (liveness/readiness) and
  `/api/v1/metrics/summary` with `verify.avg_inference_ms`, `verify.scored`,
  `verify.confirmed/suppressed`, `verify.windows`. These are exactly the
  signals an autoscaling experiment needs.
- LSTM-AE inference is **CPU-bound** in the current build (numpy artifact, no
  GPU, no deep-learning runtime). CPU utilization is therefore a legitimate
  proxy for verification load — enabling a CPU-based HPA with zero extra infra.

The edge gateway is deliberately **not** a scale target: it is bound to a
single MQTT subscription and stateful ordering, so horizontal replicas would
compete on the same broker topic. Keep it a single replica.

## 3. Target architecture

```
                         Kubernetes cluster (kind / k3d, single node)
  ┌──────────────────────────────────────────────────────────────────┐
  │                                                                    │
  │  mosquitto (Deployment, 1)     grafana (Deployment, 1)            │
  │        │                              │                            │
  │  edge-gateway (Deployment, 1) ── escalations HTTP ──┐             │
  │        │                                            ▼             │
  │  timescaledb (StatefulSet, 1 + PVC)      cloud-tier (Deployment)  │
  │                                          ▲   N replicas           │
  │                                          │   HorizontalPodAutoscaler│
  │  simulator (Job, load driver) ───────────┘   (CPU or custom metric)│
  │                                                                    │
  └──────────────────────────────────────────────────────────────────┘
```

Mapping from the existing `docker-compose.yml`:

| Compose service | K8s object | Notes |
|---|---|---|
| `cloud-tier` | Deployment + Service + **HPA** | scale target; set CPU requests/limits (HPA needs requests) |
| `timescaledb` | StatefulSet + PVC + headless Service | only stateful component; 1 replica |
| `mosquitto` | Deployment + Service | 1 replica |
| `edge-gateway` | Deployment + Service | 1 replica; env from ConfigMap/Secret |
| `grafana` | Deployment + Service + PVC (optional) | 1 replica; can drop for the experiment |
| `simulator` (loadtest profile) | Job (or parallel Jobs) | load driver; parametrize scenario + rate |
| `.env` | ConfigMap + Secret | non-secret env → ConfigMap; DB creds → Secret |
| named volumes | PVCs | `timescale-data` is the one that matters |
| model artifacts (`./models`) | bake into image **or** ConfigMap/PVC | prefer baking `cloud_lstm_ae.npz` into the cloud image for immutability |

## 4. Deliverables (repository layout)

```
k8s/
  namespace.yaml
  configmap-gateway.yaml         # gateway env (from .env non-secrets)
  secret-timescaledb.yaml        # DB creds (kept out of git; template only)
  mosquitto.deployment.yaml + service
  timescaledb.statefulset.yaml + service + pvc
  edge-gateway.deployment.yaml + service
  cloud-tier.deployment.yaml + service
  cloud-tier.hpa.yaml            # HorizontalPodAutoscaler
  simulator.job.yaml             # templated load driver
  kustomization.yaml             # ties it together; overlays for experiment
scripts/
  run_k8s_scaling_test.sh        # sweep escalation load, capture results
  lib/k8s_common.sh              # kubectl helpers (mirrors lib/common.sh)
results/
  k8s_scaling/                   # pinned result JSONs (like other phases)
docs/thesis/notes/
  2026-07-05-phase4-kubernetes-plan.md   # this file
  (later) YYYY-MM-DD-phase4-k8s-scaling.md  # results write-up
```

Model shipping decision: **bake the artifact into `cloud/Dockerfile`** (COPY
`models/cloud_lstm_ae.npz`) rather than mounting a hostPath. It keeps the image
self-contained, which is what makes replica scale-out trivial. This is a small
change to the existing Dockerfile (currently it only COPYs `app`).

## 5. The autoscaling signal — two paths

Start with **A**, document **B** as the more principled option.

**A. CPU-based HPA (recommended first).**
- Requires `metrics-server` in the cluster (one manifest; `kind` needs the
  `--kubelet-insecure-tls` arg).
- Set CPU `requests` on the cloud-tier container (e.g. 250m) — HPA scales on
  utilization relative to requests.
- `cloud-tier.hpa.yaml`: `minReplicas: 1`, `maxReplicas: 6`,
  `averageUtilization: 60`.
- Honest framing: CPU util is a *proxy* for verification load because inference
  is CPU-bound. State this explicitly.

**B. Custom-metric HPA on `verify.avg_inference_ms` (future/optional).**
- Requires `prometheus` + `prometheus-adapter`; expose the metric in Prometheus
  format (add a `/metrics` endpoint to the FastAPI app or scrape the summary).
- More "correct" (scales on the actual SLO) but materially more setup.
- Recommend: implement A for the thesis result; describe B as an extension.

## 6. Experiment design

Independent variable: **escalation load** offered to the cloud tier. Two ways
to drive it, pick one and hold the other constant:
1. Escalation *rate* — run the simulator at increasing message rates so more
   readings cross the gate (realistic; couples to the whole pipeline).
2. Direct load — bypass the gateway and POST synthetic escalation envelopes
   straight to the cloud-tier Service at controlled RPS (cleaner isolation of
   the scale target). **Recommended for the core result**, with one end-to-end
   run through the gateway as a realism check.

Dependent variables (per load level):
- replica count over time (`kubectl get hpa`, `kubectl get deploy`)
- p50/p95 verification latency (`verify.avg_inference_ms`, plus client-side
  request latency percentiles from the load driver)
- throughput (readings verified/sec = `verify.scored` delta / interval)
- verdict correctness sanity (`confirmed`/`suppressed` counts stay consistent
  with the Phase 3 offline numbers — scaling must not change verdicts)

Procedure (mirrors the existing `run_*_test.sh` convention):
1. `run_k8s_scaling_test.sh` applies the manifests, waits for rollout
   (`kubectl rollout status`), and confirms `metrics-server` is live.
2. Sweep load levels L1..Ln (e.g. 5 steps). At each: hold for a warm-up +
   steady window, poll `/api/v1/metrics/summary` and HPA state on an interval,
   snapshot to `results/k8s_scaling/L{n}.json`.
3. Compute a summary (`k8s-scaling-summary.json`): for each level, offered
   load, steady replica count, p95 latency, throughput. This is the thesis
   table.
4. Tear down (`kubectl delete -k k8s/` or delete namespace).

Acceptance criteria (what makes the result thesis-worthy):
- Replica count increases monotonically with load (autoscaling actually fires).
- p95 verification latency stays bounded (roughly flat) across load levels once
  scaled — the headline "elasticity holds latency" claim.
- Verdict distribution stays consistent with Phase 3 — scaling is correctness-
  neutral.
- If latency is NOT held (e.g. cold-start/scale-up lag dominates), report that
  honestly: it is still a valid finding about HPA reaction time.

## 7. Harness notes (new code, not a port)

The existing harness is `docker compose`-native (`docker compose run --rm
simulator`, `docker compose exec timescaledb`, `wait_for_timescaledb`). Phase 4
needs **parallel** `kubectl`-based helpers in `scripts/lib/k8s_common.sh`:
- `wait_for_rollout <deploy>` → `kubectl rollout status`
- `wait_for_service <svc> <path>` → port-forward or NodePort + curl
- `run_migrations` → `kubectl exec` into the timescaledb pod (or a migration
  Job) instead of the compose exec form
- metrics access → `kubectl port-forward svc/cloud-tier` or a NodePort

Budget for this as genuinely new harness code. Keep the compose stack working
in parallel — Phase 4 is additive; do not delete `docker-compose.yml`.

## 8. Suggested 3-month timeline

- **Weeks 1–2 — Iterate current version.** Finish testing/iterating Phases 1–3
  (the stated near-term priority). No K8s work yet.
- **Weeks 3–4 — Local cluster + lift-and-shift.** Stand up `kind`/`k3d`, write
  base manifests, get the full stack running on K8s with parity to compose
  (no autoscaling yet). Milestone: an end-to-end escalation run works on K8s.
- **Weeks 5–6 — Autoscaling.** Add `metrics-server`, CPU requests, and the HPA.
  Manually confirm scale-up/down under a crude load. Milestone: HPA fires.
- **Weeks 7–8 — Experiment harness.** `run_k8s_scaling_test.sh` +
  `lib/k8s_common.sh`, load driver (direct-POST mode), result JSON schema.
- **Weeks 9–10 — Measurement runs.** Sweep load, collect, sanity-check verdicts,
  re-run for stability. Pin result JSONs under `results/k8s_scaling/`.
- **Weeks 11–12 — Write-up.** Results notes doc + thesis sections (see §9),
  figures (scaling curve, latency-under-scale table). Buffer for iteration.

Cut lines if time runs short, in priority order: drop custom-metric HPA (keep
CPU), drop the end-to-end-through-gateway realism run (keep direct-POST), drop
Grafana from the cluster.

## 9. Thesis integration

- **Ch. 3 (Architecture):** add a Kubernetes deployment subsection — the
  service→object mapping and why the verifier is the scale target.
- **Ch. 4 (Methodology):** the manifests, HPA config, and the scaling-test
  harness.
- **Ch. 5 (Evaluation):** Phase 4 experiment design (this §6).
- **Ch. 6 (Results):** new section 6.7.4 — elastic scaling results (curve +
  table). Keep claims scoped to the local cluster.
- **Ch. 7:** update the roadmap bullet (done: 7.4 now lists Phase 4 as K8s
  elastic scaling; storage optimization moved to 7.6 open future work).

## 10. Risks / honesty guardrails

- Single-node `kind` shares one host's CPU across "replicas" — scaling relieves
  per-process contention but is not true horizontal hardware scale-out. **State
  this plainly.** It demonstrates the autoscaling *mechanism* and latency
  behaviour, not datacenter-grade capacity.
- Do not claim fault tolerance / HA unless pods are actually killed and recovery
  measured. Out of scope for the core result.
- Do not claim production readiness. Phase 4 is a controlled scaling experiment,
  same spirit as the simulator-based Phases 1–3.
- Verdict correctness must be checked, not assumed — a scaling change that
  altered detection would invalidate the result.
