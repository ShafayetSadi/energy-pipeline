---
theme: default
title: "WattFlow: Current Project Status"
titleTemplate: "%s"
author: "Shafayetul Huda Sadi"
keywords: "smart energy monitoring, STM32, MQTT, edge-cloud pipeline, anomaly detection"
info: |
  Current-status thesis presentation for WattFlow.
aspectRatio: 16/9
canvasWidth: 1280
colorSchema: light
transition: fade
duration: 15min
presenter: true
drawings:
  enabled: presenter
  persist: false
exportFilename: wattflow-current-status
download: false
---

<div class="cover-shell">
  <div class="cover-main">
    <div class="kicker">Thesis project · current status</div>
    <h1>WattFlow</h1>
    <div class="cover-subtitle">An event-driven edge–cloud pipeline for real-time energy monitoring using STM32</div>
    <div class="cover-tags"><span>STM32 + MQTT</span><span>Edge intelligence</span><span>Cloud verification</span></div>
  </div>
  <div class="cover-visual" aria-label="Energy monitoring pipeline">
    <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div>
    <div class="cover-core"><small>PIPELINE</small><strong>EDGE<br>↕<br>CLOUD</strong></div>
    <div class="orbit-node node-sense">Sense</div><div class="orbit-node node-process">Events</div><div class="orbit-node node-detect">Verify</div>
    <div class="phase-status"><span></span> Software Phases 1–3 evaluated</div>
  </div>
</div>

<div class="identity-grid">
  <div class="identity-item"><span>Presented by</span><strong>Shafayetul Huda Sadi</strong><small>Student ID · 2110057</small></div>
  <div class="identity-item"><span>Department</span><strong>Department of ECE</strong><small>RUET</small></div>
  <div class="identity-item"><span>Supervisor</span><strong>Prof. Dr. Md. Anwar Hossain</strong><small>Professor · Department of ECE</small></div>
</div>

---

<div class="section-label">Research focus</div>

# The problem, aim, and questions

<div class="grid-2-wide">
  <div>
    <div class="card problem"><h3>Problem</h3><p>Continuous energy telemetry is useful only if invalid readings, operational violations, and anomalous behavior become timely, trustworthy evidence.</p></div>
    <div class="card solution" style="margin-top: 14px"><h3>Aim</h3><p>Design and evaluate an event-driven edge–cloud data pipeline for real-time energy monitoring using STM32.</p></div>
  </div>
  <div class="card research">
    <h3>Research questions</h3>
    <ol class="small">
      <li>How should sensing, edge processing, and cloud verification be partitioned?</li>
      <li>What ingestion overhead does validation, event detection, and asynchronous ML add?</li>
      <li>Can selective forwarding and cloud verification improve evidence quality without blocking ingestion?</li>
    </ol>
  </div>
</div>

<div class="callout" style="margin-top: 22px">The contribution is an integrated, measured system—not a claim of a new anomaly-detection algorithm or a nationwide deployment.</div>

---

<div class="section-label">Current architecture</div>

# What is implemented now

```mermaid {scale: 0.78, theme: 'neutral'}
flowchart LR
  FW["STM32F411 Black Pill<br/>or scenario simulator"] -->|MQTT telemetry + status| M["Mosquitto"]
  M --> G["FastAPI edge gateway<br/>validate · detect · persist"]
  G --> DB[("TimescaleDB")]
  DB --> GF["Grafana<br/>5 dashboards"]
  G --> A["Durable alert outbox<br/>console · webhook · Slack"]
  G -. "optional async scored batches" .-> C["Cloud verifier API<br/>windowed LSTM-autoencoder"]
  C --> S["Bounded in-memory<br/>verdicts · counters"]
```

<p class="figure-caption">Detection and persistence remain available at the edge. The optional cloud verifier is not on the critical ingestion path and is not a durable system of record.</p>

---

<div class="section-label">Edge processing</div>

# One telemetry message, two evidence paths

```mermaid {scale: 0.76, theme: 'neutral'}
flowchart LR
  IN["MQTT telemetry"] --> V["Decode + validate"]
  V -->|invalid| Q[("Data-quality log")]
  V -->|valid| R["Six YAML rules"]
  R --> P["Storage policy"]
  P --> D[("Reading")]
  R -->|rule hit| E[("Event")]
  R -. "optional" .-> MQ["Async ML queue"]
  MQ --> IF["Isolation Forest"] --> PR[("Prediction")]
  E --> O["Durable alert outbox"]
  PR -. "gated or all" .-> CV["Cloud verifier"]
```

<div class="grid-3" style="margin-top: 16px">
  <div class="card compact solution"><strong>Validation</strong><br><span class="tiny muted">Reject malformed, out-of-range, and contract-inconsistent payloads.</span></div>
  <div class="card compact research"><strong>Detection</strong><br><span class="tiny muted">Rules cover known limits; ML adds distribution-based evidence.</span></div>
  <div class="card compact future"><strong>Boundary</strong><br><span class="tiny muted">Cloud verdicts are currently process memory and clear on restart.</span></div>
</div>

---

<div class="section-label">Hardware path</div>

# Current physical-node design: ready for bench validation

<div class="grid-2-wide">
  <div class="card research">
    <h3>STM32F411 “Black Pill” node</h3>
    <ul class="small">
      <li>ZMPT101B voltage sensing; ACS712-5A current sensing, with SCT-013-000 as a backup option.</li>
      <li>Timer-triggered two-channel ADC + DMA at 3.2 kHz.</li>
      <li>On-device RMS, real power, and power-factor calculation.</li>
      <li>ESP-01 acts as a UART-to-MQTT Wi-Fi bridge; STM32 owns the metrology.</li>
    </ul>
  </div>
  <div>
    <div class="card solution"><span class="badge validated">Verified</span><h3 style="margin-top: 10px">Metrology core</h3><p class="small">Host tests passed for 230 V / 5 A resistive input, 60° lagging power factor, and empty-input guard behavior.</p></div>
    <div class="card future" style="margin-top: 14px"><span class="badge pending">Pending</span><h3 style="margin-top: 10px">Physical evidence</h3><p class="small">Low-voltage bench integration, MQTT end-to-end device run, multimeter calibration, and safe mains testing are not yet evidenced.</p></div>
  </div>
</div>

<div class="callout warning" style="margin-top: 18px">The deck does not claim field metering accuracy. Calibration must be reported against a multimeter after physical assembly.</div>

---

<div class="section-label">Implementation status</div>

# What is complete, optional, and still open

<div>
  <div class="status-row header"><div>Area</div><div>Status</div><div>Evidence boundary</div></div>
  <div class="status-row"><div>MQTT → database pipeline</div><div><span class="badge validated">Implemented</span></div><div>FastAPI, Mosquitto, Alembic, TimescaleDB</div></div>
  <div class="status-row"><div>Rules, alerts, dashboards</div><div><span class="badge validated">Implemented</span></div><div>Six rules, durable outbox, five Grafana dashboards</div></div>
  <div class="status-row"><div>Edge ML · Phase 1</div><div><span class="badge done">Evaluated</span></div><div>Isolation Forest with inline/asynchronous scoring; off by default</div></div>
  <div class="status-row"><div>Cloud gate · Phase 2</div><div><span class="badge done">Evaluated</span></div><div>Gated/all forwarding with application-payload byte counters; off by default</div></div>
  <div class="status-row"><div>Cloud verifier · Phase 3</div><div><span class="badge done">Evaluated</span></div><div>Optional LSTM-autoencoder; recent state is in memory only</div></div>
  <div class="status-row"><div>Physical meter / production security</div><div><span class="badge pending">Open</span></div><div>No calibrated field node, API auth, MQTT TLS, or device credentials</div></div>
</div>

---

<div class="section-label">Evaluation design</div>

# Reproducible evidence, with explicit boundaries

<div class="grid-2">
  <div class="card solution">
    <h3>Measured lanes</h3>
    <ul class="small">
      <li>Repeated baseline vs proposed ingestion A/B</li>
      <li>Rules-only vs ML-only vs hybrid operation</li>
      <li>Gated vs all-to-cloud forwarding</li>
      <li>Offline edge-only vs two-stage cloud verification</li>
    </ul>
  </div>
  <div class="card future">
    <h3>What these results do not establish</h3>
    <ul class="small">
      <li>Field measurement accuracy or long-duration reliability</li>
      <li>Production readiness, security, or distributed elasticity</li>
      <li>Storage reduction or full wire-level bandwidth</li>
      <li>Real-world sequential ML performance</li>
    </ul>
  </div>
</div>

<p class="figure-caption" style="margin-top: 20px">Headline comparisons use pinned result artifacts. Precision, recall, and false-positive claims come from labeled offline evaluation; online experiments measure operational behavior.</p>

---

<div class="section-label">Result · ingestion cost</div>

# Edge intelligence preserved matched throughput

<div class="grid-2-wide">
  <img class="img-frame no-shadow" style="max-height: 430px" src="./assets/fig5_ingest_overhead.png" alt="Baseline versus proposed ingestion latency">
  <div>
    <div class="metric" style="margin-bottom: 14px"><span class="value">≈202 msg/s</span><span class="label">matched simulator throughput</span></div>
    <div class="metric" style="margin-bottom: 14px"><span class="value">+0.32 ms</span><span class="label">average proposed-mode overhead</span></div>
    <div class="metric"><span class="value">3 + 3 runs</span><span class="label">baseline and proposed repetitions</span></div>
  </div>
</div>

<div class="callout" style="margin-top: 16px">Under this controlled load, validation, rules, events, and observability added a small ingestion overhead without reducing the matched throughput.</div>

---

<div class="section-label">Result · edge intelligence</div>

# Asynchronous scoring protects the ingest path

<div class="grid-2-wide">
  <img class="img-frame no-shadow" style="max-height: 420px" src="./assets/fig4_async_decoupling.png" alt="Asynchronous edge ML scoring">
  <div>
    <div class="metric-grid" style="grid-template-columns: 1fr 1fr">
      <div class="metric"><span class="value">6.35 ms</span><span class="label">ML-mode ingest average</span></div>
      <div class="metric"><span class="value">10.35 ms</span><span class="label">ML-mode ingest p99</span></div>
      <div class="metric"><span class="value">≈49 ms</span><span class="label">enqueue-to-score delay</span></div>
      <div class="metric"><span class="value">50 ms</span><span class="label">configured batch window</span></div>
    </div>
    <p class="small muted" style="margin-top: 18px">The cost moves into a bounded asynchronous queue instead of blocking each incoming telemetry message.</p>
  </div>
</div>

---

<div class="section-label">Result · cloud path</div>

# Selective forwarding and cloud verification improved the evidence trade-off

<div class="metric-grid">
  <div class="metric"><span class="value">−53.1%</span><span class="label">application-payload bytes vs all-to-cloud</span></div>
  <div class="metric"><span class="value">0.910</span><span class="label">two-stage offline precision</span></div>
  <div class="metric"><span class="value">0.838</span><span class="label">two-stage offline F1</span></div>
  <div class="metric"><span class="value">643</span><span class="label">edge false positives suppressed offline</span></div>
</div>

<div class="grid-2" style="margin-top: 24px">
  <div class="card solution"><h3>Phase 2 · score-gated forwarding</h3><p class="small">The controlled run sent 623 readings / 211,955 bytes with gating, versus 1,378 readings / 452,381 bytes in all-to-cloud mode.</p></div>
  <div class="card research"><h3>Phase 3 · two-stage verifier</h3><p class="small">On the labeled held-out set, precision increased from 0.663 to 0.910 while recall changed from 0.783 to 0.776.</p></div>
</div>

<div class="callout warning" style="margin-top: 18px">The bandwidth comparison is online application-payload evidence; verification quality is offline synthetic-data evidence. They should not be conflated.</div>

---

<div class="section-label">Thesis position</div>

# The defensible current claim

<div class="quote-claim">WattFlow is an edge-first, event-driven observability pipeline for energy monitoring. The evaluated software path validates telemetry, creates local operational evidence, selectively forwards scored batches, and optionally verifies them in the cloud without placing cloud work on the ingestion critical path.</div>

<div class="grid-3" style="margin-top: 24px">
  <div class="card solution"><h3>Supported</h3><p class="small">Implemented edge pipeline and controlled Phases 1–3 software evidence.</p></div>
  <div class="card future"><h3>Not yet supported</h3><p class="small">Calibrated field hardware, durable cloud archival, production security, or nationwide operation.</p></div>
  <div class="card research"><h3>Research value</h3><p class="small">A reproducible architecture with measured performance and evidence-quality trade-offs.</p></div>
</div>

---

<div class="section-label">Remaining work</div>

# Next milestones

<div class="grid-2-wide">
  <div class="card research">
    <h3>Priority implementation evidence</h3>
    <ol class="small">
      <li>Assemble and validate the Black Pill node on low-voltage AC.</li>
      <li>Calibrate against a multimeter across several loads; report error and power factor.</li>
      <li>Demonstrate physical MQTT-to-dashboard flow before any safe mains test.</li>
      <li>Repeat selected performance experiments after physical integration.</li>
    </ol>
  </div>
  <div class="card future">
    <h3>Scope decisions</h3>
    <ul class="small">
      <li>Whether durable cloud archival is required beyond the evaluated verifier.</li>
      <li>Whether production security is thesis scope or explicitly future work.</li>
      <li>How much physical calibration evidence is required for submission.</li>
      <li>Whether Kubernetes autoscaling remains a future extension.</li>
    </ul>
  </div>
</div>

---

<div class="section-label" style="text-align: center">Conclusion</div>

# From telemetry to defensible energy evidence

<div class="quote-claim" style="max-width: 1020px; margin: 32px auto">The software pipeline is implemented and evaluated through edge detection, selective cloud forwarding, and optional cloud verification. The next thesis-critical evidence is a calibrated physical measurement node—not a broader architecture rewrite.</div>

<p class="lead"><strong>Questions and scope discussion</strong></p>
