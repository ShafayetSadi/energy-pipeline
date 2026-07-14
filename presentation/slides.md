---
theme: default
title: "Design and Evaluation of an Event-Driven Edge-Cloud Data Pipeline for Real-Time Energy Monitoring using STM32"
titleTemplate: "%s"
author: "Shafayetul Huda Sadi"
keywords: "smart energy monitoring, STM32, edge-cloud pipeline, MQTT, anomaly detection, Slidev"
info: |
  Thesis idea and current progress presentation for WattFlow.
aspectRatio: 16/9
canvasWidth: 1280
colorSchema: light
transition: fade
duration: 20min
presenter: true
drawings:
  enabled: presenter
  persist: false
exportFilename: wattflow-thesis-presentation
download: false
---

<div class="cover-shell">
  <div class="cover-main">
    <div class="kicker">Thesis idea submission · Phase 1 progress</div>
    <h1>WattFlow</h1>
    <div class="cover-subtitle">
      Design and Evaluation of an Event-Driven Edge–Cloud Data Pipeline for Real-Time Energy Monitoring using STM32
    </div>
    <div class="cover-tags">
      <span>STM32 + MQTT</span>
      <span>Event-driven edge gateway</span>
      <span>Real-time energy monitoring</span>
    </div>
  </div>

  <div class="cover-visual" aria-label="STM32-to-edge-to-cloud monitoring pipeline">
    <div class="orbit orbit-one"></div>
    <div class="orbit orbit-two"></div>
    <div class="cover-core"><small>PIPELINE</small><strong>EDGE<br>↕<br>CLOUD</strong></div>
    <div class="orbit-node node-sense">STM32</div>
    <div class="orbit-node node-process">Events</div>
    <div class="orbit-node node-detect">Monitor</div>
    <div class="phase-status"><span></span> Phase 1 complete</div>
  </div>
</div>

<div class="identity-grid">
  <div class="identity-item"><span>Presented by</span><strong>Shafayetul Huda Sadi</strong><small>Student ID · 2110057</small></div>
  <div class="identity-item"><span>Department</span><strong>Department of ECE</strong><small>RUET</small></div>
  <div class="identity-item"><span>Institution</span><strong>Rajshahi University of Engineering &amp; Technology</strong><small>Rajshahi, Bangladesh</small></div>
  <div class="identity-item"><span>Supervisor</span><strong>Prof. Dr. Md. Anwar Hossain</strong><small>Professor · Department of ECE</small></div>
</div>

<!--
Introduce this as both an idea submission and a continuity briefing for the new supervisor.
The original thesis title is retained, while the progress section clearly limits completed work to Phase 1.
-->

---

<div class="section-label">Thesis vision</div>

# A national energy intelligence platform for Bangladesh

<div class="vision-dashboard">
  <div class="vision-copy">
    <div class="vision-eyebrow">From one monitored node to one national energy picture</div>
    <div class="vision-statement">
      Connect distributed energy data in a single scalable platform for <strong>real-time collection</strong>, <strong>unified analysis</strong>, and future <strong>prediction</strong>.
    </div>
    <div class="phase-foundation">
      <span>Thesis focus · Phase 1 evidence</span>
      <strong>Design and evaluate the STM32-to-edge-to-cloud monitoring pipeline</strong>
      <small>STM32 sensing → MQTT → event-driven edge processing → cloud evidence</small>
    </div>
    <div class="scale-path">
      <div><span class="active"></span><strong>Edge node</strong></div>
      <i></i>
      <div><span></span><strong>Multi-site</strong></div>
      <i></i>
      <div><span></span><strong>Nationwide</strong></div>
    </div>
  </div>

  <div class="national-platform">
    <div class="platform-label">Long-term system vision</div>
    <svg class="platform-links" viewBox="0 0 430 255" aria-hidden="true">
      <line x1="215" y1="128" x2="88" y2="58" />
      <line x1="215" y1="128" x2="342" y2="58" />
      <line x1="215" y1="128" x2="88" y2="198" />
      <line x1="215" y1="128" x2="342" y2="198" />
    </svg>
    <div class="platform-core"><small>BANGLADESH</small><strong>ONE<br>ENERGY<br>VIEW</strong></div>
    <div class="platform-node generation"><span></span>Generation</div>
    <div class="platform-node grid"><span></span>Grid</div>
    <div class="platform-node industry"><span></span>Industry</div>
    <div class="platform-node consumer"><span></span>Consumers</div>
    <div class="platform-caption">Shared telemetry · events · analytics</div>
  </div>
</div>

<div class="vision-pillars">
  <div class="vision-pillar"><span>01</span><strong>Collect</strong><small>Distributed, near-real-time energy telemetry</small></div>
  <div class="vision-pillar"><span>02</span><strong>Unify</strong><small>One observable data and event model</small></div>
  <div class="vision-pillar"><span>03</span><strong>Analyze</strong><small>Quality, events, anomalies, and trends</small></div>
  <div class="vision-pillar future"><span>04</span><strong>Predict</strong><small>Demand, failures, and system risk</small></div>
</div>

<!--
Present the nationwide platform as the north-star vision, not as a result already delivered. Phase 1 is the measurable foundation built in this thesis.
-->

---

<div class="section-label">Motivation · Original thesis problem</div>

# Why an event-driven edge–cloud pipeline?

<div class="problem-hero">
  <div class="problem-signal" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
  <div class="problem-hero-block">
    <span>Starting point</span>
    <strong>Continuous STM32 energy telemetry</strong>
  </div>
  <div class="problem-hero-arrow">→</div>
  <div class="problem-hero-block research-need">
    <span>Research need</span>
    <strong>Timely, trustworthy, and scalable energy evidence</strong>
  </div>
</div>

<div class="problem-grid">
  <div class="problem-card">
    <div class="problem-card-top"><span>01</span><b>≈</b></div>
    <h3>Data never stops</h3>
    <p>Voltage, current, power, and status arrive continuously. A store-everything path treats normal and critical readings identically.</p>
    <small>Risk · critical readings look ordinary</small>
  </div>
  <div class="problem-card">
    <div class="problem-card-top"><span>02</span><b>!</b></div>
    <h3>Events are recognized late</h3>
    <p>If processing begins only after cloud storage, overload, voltage deviation, invalid data, or device silence may be classified too late.</p>
    <small>Risk · response begins after storage</small>
  </div>
  <div class="problem-card">
    <div class="problem-card-top"><span>03</span><b>?</b></div>
    <h3>The system cost is unclear</h3>
    <p>Many prototypes show a dashboard, but do not measure the latency, throughput, validation, and intelligence cost of the edge–cloud split.</p>
    <small>Gap · architecture without evaluation</small>
  </div>
</div>

<div class="pipeline-compare">
  <div class="pipeline-lane baseline">
    <div class="pipeline-label"><span></span> Store-first baseline</div>
    <div class="pipeline-flow"><span>STM32</span><b>→</b><span>MQTT</span><b>→</b><span>Cloud / DB</span><b>→</b><span>Dashboard</span></div>
    <small>Store first; interpret later</small>
  </div>
  <div class="pipeline-shift"><span>SHIFT</span><b>→</b></div>
  <div class="pipeline-lane proposed">
    <div class="pipeline-label"><span></span> Thesis design</div>
    <div class="pipeline-flow"><span>STM32</span><b>→</b><span>MQTT</span><b>→</b><span class="edge-chip">Edge validate + detect</span><b>→</b><span>Cloud / view</span></div>
    <small>React locally; preserve system-wide evidence</small>
  </div>
</div>

<div class="phase-boundary">
  <div class="phase-evidence"><span class="status-dot"></span><div><strong>Phase 1 complete</strong><small>Edge gateway · rules + Isolation Forest · measured evaluation</small></div></div>
  <div class="phase-divider"></div>
  <div class="phase-next"><span>Next evidence</span><small>Physical STM32 integration · cloud handoff evaluation</small></div>
</div>

<!--
Tie each limitation to the original STM32 edge–cloud pipeline proposal. Phase 1 evaluates the edge foundation rather than claiming national deployment.
-->

---

<div class="section-label">Research positioning</div>

# Research gap

<div class="grid-2-wide">
  <div>
    <p class="lead">Prior work establishes the individual building blocks:</p>
    <div class="grid-2" style="gap: 12px; margin-top: 16px">
      <div class="card compact"><strong>STM32 / IoT metering</strong><br><span class="small muted">Connected sensing prototypes [1]</span></div>
      <div class="card compact"><strong>MQTT + cloud monitoring</strong><br><span class="small muted">Messaging and remote data access [4,5]</span></div>
      <div class="card compact"><strong>Edge / fog processing</strong><br><span class="small muted">Local response and resilience [2]</span></div>
      <div class="card compact"><strong>Energy-event detection</strong><br><span class="small muted">Rules and data-driven methods [3]</span></div>
    </div>
  </div>
  <div class="card research">
    <h3>Gap addressed by this thesis</h3>
    <p>Few prototypes evaluate the complete <strong>STM32 → MQTT → edge events → cloud evidence</strong> path as one system. This thesis measures:</p>
    <div>
      <span class="pill">throughput</span>
      <span class="pill">latency</span>
      <span class="pill">validation</span>
      <span class="pill">detection quality</span>
      <span class="pill">edge cost</span>
      <span class="pill">data movement</span>
    </div>
  </div>
</div>

<p class="tiny" style="margin-top: 16px">Research focus: an integrated architecture plus reproducible evaluation—not a new sensing device or anomaly algorithm in isolation.</p>

<!--
The gap is the measured integration, not the existence of any individual technology.
This wording is deliberately conservative and defensible.
-->

---

<div class="section-label">Research design</div>

# Aim, objectives, and questions

<div class="grid-2-wide">
  <div>
    <div class="callout">
      <strong>Aim:</strong> Design and evaluate an event-driven edge–cloud data pipeline for real-time energy monitoring using STM32.
    </div>
    <h3 style="margin-top: 20px">Objectives</h3>
    <ol class="small">
      <li>Design the STM32 sensing, processing, and MQTT telemetry contract.</li>
      <li>Implement event-driven validation and event detection at the edge.</li>
      <li>Define the edge–cloud responsibility split, storage, and visualization flow.</li>
      <li>Evaluate latency, throughput, event quality, and data-movement cost.</li>
    </ol>
  </div>
  <div>
    <div class="card research">
      <h3>RQ1 · Architecture</h3>
      <p class="small">How should sensing, event processing, and system-wide analysis be partitioned across STM32, edge, and cloud?</p>
    </div>
    <div class="card research" style="margin-top: 12px">
      <h3>RQ2 · Performance</h3>
      <p class="small">How does the event-driven design affect ingestion latency and throughput compared with a store-first baseline?</p>
    </div>
    <div class="card research" style="margin-top: 12px">
      <h3>RQ3 · Event value</h3>
      <p class="small">Can local validation and detection create timely evidence without blocking continuous telemetry or losing cloud visibility?</p>
    </div>
  </div>
</div>

<!--
RQ1–RQ3 keep the thesis centered on the complete data pipeline. Edge ML is one evaluated event-processing component.
-->

---

<div class="section-label">Evidence boundaries</div>

# What the thesis includes—and does not claim

<div class="grid-2">
  <div class="card solution">
    <h3>Thesis design and evaluation</h3>
    <ul class="small">
      <li>STM32 sensing and MQTT telemetry contract</li>
      <li>Event-driven ingestion, validation, rules, and edge ML</li>
      <li>Proposed edge–cloud responsibility and data flow</li>
      <li>Time-series persistence, events, alerts, and dashboards</li>
      <li>Controlled simulator-based A/B experiments</li>
      <li>Firmware emulation and circuit-level simulation</li>
    </ul>
  </div>
  <div class="card future">
    <h3>Not claimed as completed</h3>
    <ul class="small">
      <li>Certified billing-grade measurement accuracy</li>
      <li>Physically integrated and calibrated field hardware</li>
      <li>Long-duration production reliability</li>
      <li>Real-world sequential ML performance</li>
      <li>Full cloud integration or distributed deployment</li>
      <li>Nationwide energy-system operation</li>
      <li>Production security and device credentials</li>
    </ul>
  </div>
</div>

<div class="callout warning" style="margin-top: 18px">
  <strong>Evidence levels:</strong> edge pipeline completed · STM32 firmware emulator-validated · analog circuit simulated · full cloud path proposed · physical and nationwide deployment future.
</div>

<!--
This is an important trust slide for a new supervisor. Be explicit about what is real, simulated, and planned.
-->

---

<div class="section-label">Proposed solution</div>

# From store-first upload to edge–cloud event flow

<div class="grid-2">
  <div class="card problem">
    <h2>Baseline</h2>
    <div style="font-size: 23px; line-height: 2.2; text-align: center; margin-top: 34px">
      STM32 node<br>↓<br>MQTT broker<br>↓<br><strong>Upload and store every reading</strong><br>↓<br>Cloud dashboard
    </div>
  </div>
  <div class="card solution">
    <h2>Proposed</h2>
    <div style="font-size: 21px; line-height: 1.72; text-align: center; margin-top: 16px">
      STM32 → MQTT → edge gateway<br>↓<br><strong>Validate → detect → classify events</strong><br>↓<br>Selected telemetry + events + quality evidence<br>↓<br>Cloud aggregation · storage · dashboards
    </div>
  </div>
</div>

<p class="lead" style="margin-top: 22px; text-align: center">The evaluation measures whether earlier event processing improves timeliness and evidence quality without compromising telemetry ingestion.</p>

<!--
Define baseline carefully: it still validates enough to accept a typed reading, but disables proposed-mode rule and ML processing for the clean comparison.
-->

---

class: diagram-slide

---

<div class="section-label">Architecture</div>

# End-to-end system context

```mermaid {scale: 0.78, theme: 'neutral'}
flowchart LR
  subgraph Sources["Measurement sources"]
    AFE["Analog front end<br/>KiCad + SPICE"]
    STM["STM32F429ZI<br/>Ethernet + MQTT"]
    SIM["Scenario simulator"]
    AFE -. "future physical integration" .-> STM
  end

  subgraph Edge["Edge deployment · Phase 1 implemented"]
    MQ["Mosquitto<br/>MQTT broker"]
    GW["FastAPI edge gateway<br/>validate · detect · persist"]
    DB[("TimescaleDB")]
    GF["Grafana<br/>5 dashboards"]
    AL["Alert outbox<br/>console · webhook · Slack"]
  end

  subgraph Cloud["Cloud data platform · proposed target"]
    CI["Cloud ingress<br/>events · aggregates · selected telemetry"]
    CS[("Central time-series<br/>and event archive")]
    CA["Cross-site analytics<br/>and future prediction"]
    CV["System-wide dashboards"]
  end

  STM -->|MQTT| MQ
  SIM -->|MQTT| MQ
  MQ --> GW
  GW --> DB
  DB --> GF
  GW --> AL
  GW -. "cloud handoff" .-> CI
  CI --> CS
  CS --> CA
  CS --> CV

  classDef source fill:#ecfeff,stroke:#0891b2,color:#0b1f33;
  classDef edge fill:#eff6ff,stroke:#1d4ed8,color:#0b1f33;
  classDef cloud fill:#f8fafc,stroke:#64748b,color:#0b1f33,stroke-dasharray: 5 4;
  class AFE,STM,SIM source;
  class MQ,GW,DB,GF,AL edge;
  class CI,CS,CA,CV cloud;
```

<p class="figure-caption"><strong>Solid path:</strong> implemented Phase 1 edge foundation. <strong>Dashed handoff:</strong> proposed cloud integration for system-wide analysis.</p>

<!--
Walk left to right. The thesis architecture includes the cloud target, while current experimental evidence is concentrated at the edge.
-->

---

class: diagram-slide

---

<div class="section-label">System diagram</div>

# What happens to one MQTT reading?

```mermaid {scale: 0.76, theme: 'neutral'}
flowchart LR
  IN["MQTT telemetry"] --> PARSE["Decode + contract validation"]
  PARSE -->|invalid| QL["Data-quality log"]
  PARSE -->|valid| RULES["Evaluate YAML rules"]
  RULES --> POLICY["Apply storage policy"]
  POLICY --> READ[("Reading")]
  RULES -->|rule hit| EVT[("Event")]
  RULES -. "enqueue" .-> MLQ["Async ML queue"]
  MLQ --> IF["Isolation Forest<br/>micro-batch score"]
  IF --> PRED[("Prediction")]
  IF -->|anomalous| MLEVT[("ML event")]
  EVT --> OUTBOX["Durable alert outbox"]
  MLEVT --> OUTBOX
  READ -. "selected telemetry / aggregates" .-> HANDOFF["Cloud handoff<br/>proposed"]
  EVT -. "event evidence" .-> HANDOFF
  PRED -. "anomaly evidence" .-> HANDOFF
  HANDOFF -.-> CLOUD["Central storage<br/>cross-site analysis · dashboards"]

  classDef input fill:#ecfeff,stroke:#0891b2,color:#0b1f33;
  classDef process fill:#eff6ff,stroke:#1d4ed8,color:#0b1f33;
  classDef data fill:#f0fdf4,stroke:#15803d,color:#0b1f33;
  classDef future fill:#f8fafc,stroke:#64748b,color:#0b1f33,stroke-dasharray: 5 4;
  class IN input;
  class PARSE,RULES,POLICY,MLQ,IF,OUTBOX process;
  class QL,READ,EVT,PRED,MLEVT data;
  class HANDOFF,CLOUD future;
```

<p class="figure-caption">The completed edge path creates readings and events; the proposed handoff preserves selected evidence for cloud-scale analysis.</p>

<!--
Emphasize the two branches: invalid messages become quality evidence; valid messages continue through deterministic and optional ML processing.
-->

---

class: diagram-slide

---

<div class="section-label">Hardware system</div>

# Measurement-node signal chain

```mermaid {scale: 0.84, theme: 'neutral'}
flowchart LR
  MAINS["230 V AC<br/>and load conductor"] --> VS["ZMPT101B<br/>voltage channel"]
  MAINS --> CS["SCT-013-030<br/>current channel"]
  VS --> AFE["Isolation · scaling<br/>1.65 V bias · filtering"]
  CS --> AFE
  AFE --> ADC["STM32F429ZI ADC<br/>PA0 + PA1 · 5 kHz"]
  ADC --> DSP["Bias removal<br/>RMS · power · PF"]
  DSP --> NET["Ethernet + LwIP<br/>MQTT publisher"]
  NET --> EDGE["Edge gateway"]

  classDef hw fill:#fff7ed,stroke:#ea580c,color:#0b1f33;
  classDef fw fill:#ecfeff,stroke:#0891b2,color:#0b1f33;
  classDef sw fill:#eff6ff,stroke:#1d4ed8,color:#0b1f33;
  class MAINS,VS,CS,AFE hw;
  class ADC,DSP,NET fw;
  class EDGE sw;
```

<div class="grid-3" style="margin-top: 12px">
  <div class="card compact"><span class="badge validated">Circuit</span><br><strong>KiCad + ngspice</strong><br><span class="tiny muted">Design-value simulation</span></div>
  <div class="card compact"><span class="badge validated">Firmware</span><br><strong>STM32 + Renode</strong><br><span class="tiny muted">Real MQTT through the stack</span></div>
  <div class="card compact"><span class="badge pending">Physical node</span><br><strong>Future integration</strong><br><span class="tiny muted">Calibration and field testing</span></div>
</div>

<!--
Make the evidence boundary explicit: the circuit and firmware were validated separately, not as one physical co-simulation.
-->

---

<div class="section-label">Circuit design</div>

# Isolated voltage and current sensing front end

<img class="img-frame" style="max-height: 515px" src="./assets/energy_node_schematic.png" alt="Energy node analog front-end schematic">

<p class="figure-caption">Publication schematic: two isolated channels, matched anti-alias filters, shared 1.65 V ADC bias, and STM32F429ZI interface.</p>

<!--
Explain the four numbered regions. Mention mains safety: the voltage input requires rated isolation, protection, clearances, and enclosure. It is not a breadboard circuit.
-->

---

<div class="section-label">Edge event processing · Phase 1</div>

# Phase 1 detection modes

<div class="grid-3">
  <div class="card solution">
    <h3>1 · Deterministic rules</h3>
    <p class="small">Configurable thresholds and state logic for known violations.</p>
    <div><span class="pill">explainable</span><span class="pill">fast</span></div>
    <p class="tiny muted" style="margin-top: 12px">Overload · voltage deviation · power spike · temperature · device silence</p>
  </div>
  <div class="card research">
    <h3>2 · Edge Isolation Forest</h3>
    <p class="small">Unsupervised scoring over raw and physics-informed features.</p>
    <div><span class="pill">lightweight</span><span class="pill">adaptive</span></div>
    <p class="tiny muted" style="margin-top: 12px">$[V, I, P, T, |V-220|, P-VI]$</p>
  </div>
  <div class="card problem">
    <h3>3 · Hybrid mode</h3>
    <p class="small">Run deterministic rules and edge Isolation Forest together.</p>
    <div><span class="pill">complementary</span><span class="pill">measurable</span></div>
    <p class="tiny muted" style="margin-top: 12px">Rule events + ML anomaly evidence through the same event and alert path</p>
  </div>
</div>

<div class="callout" style="margin-top: 24px">
  Rules protect explicit operational bounds; edge ML adds distribution-based evidence; hybrid mode measures their combined behavior.
</div>

<!--
Do not describe ML as replacing rules. The thesis result is that the layers have different strengths.
-->

---

<div class="section-label">Methodology</div>

# Evaluation strategy

<div class="grid-2">
  <div class="card research">
    <h3>A · End-to-end pipeline cost</h3>
    <p class="small">200 devices · 1-second interval · approximately 120 seconds · three repetitions per mode</p>
    <div><span class="pill">throughput</span><span class="pill">avg / p95 / p99 latency</span><span class="pill">DB growth</span></div>
  </div>
  <div class="card research">
    <h3>B · Event and data quality</h3>
    <p class="small">Controlled overload, power spike, under/over-voltage, device failure, and invalid-payload streams</p>
    <div><span class="pill">event counts</span><span class="pill">validation errors</span><span class="pill">alert evidence</span></div>
  </div>
  <div class="card research">
    <h3>C · Edge processing cost</h3>
    <p class="small">Rules vs ML vs hybrid, plus inline vs asynchronous inference</p>
    <div><span class="pill">precision / recall</span><span class="pill">ingest latency</span><span class="pill">queue delay</span></div>
  </div>
  <div class="card research">
    <h3>D · Edge–cloud handoff <span class="badge planned">Planned</span></h3>
    <p class="small">Compare raw forwarding with event- and evidence-oriented cloud delivery</p>
    <div><span class="pill">forwarded volume</span><span class="pill">end-to-end delay</span><span class="pill">evidence completeness</span></div>
  </div>
</div>

<p class="figure-caption" style="margin-top: 18px">A–C have Phase 1 evidence; D completes the evaluation of the full edge–cloud thesis target.</p>

<!--
Explain independent variables and measurements. The thesis is evaluated as a system, not only demonstrated as an application.
-->

---

<div class="section-label">Expected contribution</div>

# What this thesis contributes

<div class="grid-3">
  <div class="card solution"><span class="number">1</span><strong>Architecture</strong><p class="small muted">A traceable STM32 → MQTT → edge → cloud design for real-time monitoring.</p></div>
  <div class="card solution"><span class="number">2</span><strong>Measured overhead</strong><p class="small muted">A controlled baseline/proposed comparison rather than an unmeasured prototype.</p></div>
  <div class="card solution"><span class="number">3</span><strong>Event model</strong><p class="small muted">Validated readings, quality failures, rules, and ML evidence through one observable flow.</p></div>
  <div class="card solution"><span class="number">4</span><strong>Edge intelligence</strong><p class="small muted">Measured rules and asynchronous ML as components—not the thesis identity.</p></div>
  <div class="card solution"><span class="number">5</span><strong>Reproducibility</strong><p class="small muted">Versioned configuration, migrations, experiment scripts, and pinned results.</p></div>
  <div class="card future"><span class="number">6</span><strong>Scaling path</strong><p class="small muted">A clear route from one STM32 node to multi-site and national energy views.</p></div>
</div>

<!--
If asked for novelty, emphasize the integrated and measured research method rather than claiming a new algorithm.
-->

---

<div class="section-label">Progress to date</div>

# Work completed so far

<div class="timeline">
  <div class="timeline-item">
    <div class="card compact"><span class="badge validated">Implemented</span><h3 style="margin-top: 10px">Pipeline foundation</h3><p class="small">STM32 contract, MQTT, validation, storage, dashboards, APIs, and alerts</p></div>
  </div>
  <div class="timeline-item">
    <div class="card compact"><span class="badge done">Completed</span><h3 style="margin-top: 10px">Phase 1</h3><p class="small">Edge Isolation Forest, async micro-batching, rules/ML/hybrid evaluation</p></div>
  </div>
  <div class="timeline-item">
    <div class="card compact"><span class="badge validated">Validated</span><h3 style="margin-top: 10px">Phase 1 evidence</h3><p class="small">Offline detection quality and online operational-cost measurements</p></div>
  </div>
  <div class="timeline-item future">
    <div class="card compact future"><span class="badge planned">Next</span><h3 style="margin-top: 10px">Complete edge–cloud scope</h3><p class="small">Physical node, cloud handoff, repeat runs, and thesis consolidation</p></div>
  </div>
</div>

<div class="callout" style="margin-top: 28px">
  The project has moved beyond an idea-only proposal: the current task is to align the final thesis scope with the new supervisor.
</div>

<!--
This is the transition into evidence. Clarify that completed means implemented and tested within the stated simulator/emulator scope.
-->

---

<div class="section-label">Implementation status</div>

# Phase 1 implementation status

<div>
  <div class="status-row header"><div>Area</div><div>Status</div><div>Evidence boundary</div></div>
  <div class="status-row"><div>MQTT → database pipeline</div><div><span class="badge validated">Implemented</span></div><div>FastAPI, Mosquitto, Alembic, TimescaleDB</div></div>
  <div class="status-row"><div>Rules, alerting, dashboards</div><div><span class="badge validated">Implemented</span></div><div>Six rules, durable outbox, five Grafana dashboards</div></div>
  <div class="status-row"><div>Phase 1 edge ML</div><div><span class="badge done">Complete</span></div><div>Isolation Forest, prediction storage, ML events, async worker</div></div>
  <div class="status-row"><div>STM32 firmware</div><div><span class="badge validated">Validated</span></div><div>Compiled firmware exercised end-to-end in Renode</div></div>
  <div class="status-row"><div>Analog front end</div><div><span class="badge validated">Validated</span></div><div>KiCad design and ngspice chain validation</div></div>
  <div class="status-row"><div>Physical calibrated meter</div><div><span class="badge pending">Pending</span></div><div>No integrated field hardware or certified accuracy claim</div></div>
  <div class="status-row"><div>Cloud pipeline integration</div><div><span class="badge planned">Proposed</span></div><div>Responsibility and handoff defined; implementation/evaluation pending</div></div>
  <div class="status-row"><div>Nationwide platform</div><div><span class="badge planned">Vision</span></div><div>Long-term motivation, outside the completed thesis evidence</div></div>
</div>

<!--
This table is aligned to the current architecture document. Do not replace these statuses with a single completion percentage.
-->

---

<div class="section-label">Preliminary result · system cost</div>

# Edge intelligence adds a small ingest overhead

<div class="grid-2-wide">
  <div>
    <img class="img-frame no-shadow" style="max-height: 440px" src="./assets/fig5_ingest_overhead.png" alt="Baseline versus proposed ingestion latency">
  </div>
  <div>
    <div class="metric" style="margin-bottom: 14px"><span class="value">≈202 msg/s</span><span class="label">matched simulator throughput</span></div>
    <div class="metric" style="margin-bottom: 14px"><span class="value">+0.32 ms</span><span class="label">average proposed-mode overhead</span></div>
    <div class="metric"><span class="value">3 + 3 runs</span><span class="label">baseline and proposed repetitions</span></div>
  </div>
</div>

<div class="callout" style="margin-top: 14px">The proposed gateway preserved throughput while adding validation, rules, event evidence, and observability.</div>

<!--
State that these are local Docker experiments. The result supports low overhead under this tested load, not universal scalability.
-->

---

<div class="section-label">Phase 1 result · detection quality</div>

# Edge Isolation Forest: offline evaluation

<div class="metric-grid">
  <div class="metric"><span class="value">0.612</span><span class="label">precision</span></div>
  <div class="metric"><span class="value">0.780</span><span class="label">recall</span></div>
  <div class="metric"><span class="value">0.686</span><span class="label">F1 score</span></div>
  <div class="metric"><span class="value">0.099</span><span class="label">false-positive rate</span></div>
</div>

<div class="grid-2" style="margin-top: 24px">
  <div class="card solution"><h3>Detected well</h3><p class="small">Over-voltage 0.99 · power spike 0.86 · under-voltage 0.83 recall</p></div>
  <div class="card problem"><h3>Important weakness</h3><p class="small">Overload recall was 0.44 because the simulated normal load already overlaps the fixed overload region.</p></div>
</div>

<div class="callout warning" style="margin-top: 18px">Offline result on simulator-faithful synthetic data; it is not a field-accuracy claim.</div>

<!--
The weak overload result is useful rather than embarrassing: it shows that a fixed rule and a distribution-based model answer different questions.
-->

---

<div class="section-label">Phase 1 result · operational cost</div>

# Asynchronous scoring protects ingestion latency

<div class="grid-2-wide">
  <div>
    <img class="img-frame no-shadow" style="max-height: 430px" src="./assets/fig4_async_decoupling.png" alt="Inline versus asynchronous edge ML scoring">
  </div>
  <div>
    <div class="metric-grid" style="grid-template-columns: 1fr 1fr; margin-bottom: 16px">
      <div class="metric"><span class="value">6.35 ms</span><span class="label">ML-mode ingest average</span></div>
      <div class="metric"><span class="value">10.35 ms</span><span class="label">ML-mode ingest p99</span></div>
      <div class="metric"><span class="value">≈49 ms</span><span class="label">enqueue-to-score delay</span></div>
      <div class="metric"><span class="value">50 ms</span><span class="label">configured batch window</span></div>
    </div>
    <p class="small muted">The inference cost moved away from the synchronous telemetry path into a bounded asynchronous queue.</p>
  </div>
</div>

<!--
This experiment demonstrates decoupling, not high-throughput batch amortisation; the tested anomaly stream averaged only about 2.3 messages per second.
-->

---

<div class="section-label">Interpretation</div>

# What the evidence supports

<div class="grid-3">
  <div class="card solution">
    <h3>Pipeline claim</h3>
    <p>The implemented event-driven edge path preserves throughput with low measured ingestion overhead.</p>
  </div>
  <div class="card research">
    <h3>Event claim</h3>
    <p>Validation, rules, and ML produce complementary operational evidence.</p>
  </div>
  <div class="card problem">
    <h3>Architecture claim</h3>
    <p>Asynchronous work supports a responsive edge tier; the cloud handoff remains to be evaluated.</p>
  </div>
</div>

<div class="quote-claim" style="font-size: 23px">
The defensible contribution is the designed STM32 edge–cloud architecture and measured Phase 1 edge foundation—not a claim of completed cloud or national deployment.
</div>

<!--
This is the key synthesis. Pause here and let the three claims land before moving to limitations.
-->

---

<div class="section-label">Limitations</div>

# Where the conclusions stop

<div class="grid-2">
  <div class="card future">
    <h3>Experimental limitations</h3>
    <ul class="small">
      <li>Simulator-derived data and short local Docker runs</li>
      <li>Single global edge model rather than per-device models</li>
      <li>Offline labels come from simulator-derived synthetic scenarios</li>
      <li>Online A/B runs need additional repetitions at higher rates</li>
    </ul>
  </div>
  <div class="card future">
    <h3>Engineering limitations</h3>
    <ul class="small">
      <li>No integrated, calibrated physical sensing node</li>
      <li>No MQTT TLS, API authorization, or per-device credentials</li>
      <li>Edge model is not yet optimized for a constrained physical target</li>
      <li>No production deployment or long-duration soak evidence</li>
      <li>No implemented or measured cloud handoff yet</li>
    </ul>
  </div>
</div>

<div class="callout warning" style="margin-top: 18px">The current results do not prove storage reduction; additional prediction and event evidence can increase database growth.</div>

<!--
Limitations strengthen the thesis when they are connected to concrete next experiments.
-->

---

<div class="section-label">Next steps</div>

# Proposed remaining work and scope decisions

<div class="grid-2-wide">
  <div>
    <h3>Recommended priority</h3>
    <ol>
      <li><strong>Freeze the STM32 edge–cloud title and evidence scope</strong> with the new supervisor.</li>
      <li>Integrate and calibrate one physical STM32 sensing node, if feasible.</li>
      <li>Implement the cloud handoff and central aggregation path.</li>
      <li>Repeat end-to-end latency, throughput, and data-movement experiments.</li>
      <li>Consolidate chapters, figures, citations, and reproducibility artifacts.</li>
    </ol>
  </div>
  <div class="card research">
    <h3>Questions for supervisor alignment</h3>
    <ul class="small">
      <li>Is the proposed title and edge–cloud scope appropriately focused?</li>
      <li>How much physical hardware evidence is required?</li>
      <li>Should the next experiment prioritize physical STM32 integration or the cloud handoff?</li>
      <li>What minimum cloud implementation is required to support the title?</li>
      <li>What milestones and submission dates should govern the remaining work?</li>
    </ul>
  </div>
</div>

<!--
Ask for decisions, not only feedback. The current presentation deliberately stops at the completed Phase 1 scope.
-->

---

layout: center
class: text-center

---

<div class="section-label">Proposed thesis claim</div>

# An event-driven STM32 edge–cloud pipeline

<div class="quote-claim" style="max-width: 1050px; margin: 28px auto">
WattFlow designs an STM32-to-edge-to-cloud pipeline for real-time energy monitoring. Phase 1 shows that event-driven validation, rules, and lightweight ML can run at the edge with small measured overhead; physical integration and full cloud-path evaluation are the next evidence milestones.
</div>

<p class="lead"><strong>Questions and scope discussion</strong></p>

<!--
End on the claim, then invite the supervisor to discuss scope. Do not end on the limitations slide.
-->

---

layout: center
class: text-center

---

<div class="section-label">Appendix</div>

# Supporting technical evidence

<p class="lead">Use the following slides for questions about circuit validation, ML latency, internal architecture, implementation choices, and sources.</p>

---

<div class="section-label">Appendix A · Circuit evidence</div>

# SPICE-to-firmware measurement-chain validation

<div class="grid-2-wide">
  <div>
    <img class="img-frame no-shadow" style="max-height: 440px" src="./assets/frontend_waveforms.png" alt="SPICE front-end ADC waveforms">
  </div>
  <div>
    <table>
      <thead><tr><th>Quantity</th><th>True</th><th>Recovered</th><th>Error</th></tr></thead>
      <tbody>
        <tr><td>$V_{rms}$</td><td>230 V</td><td>226.8 V</td><td>−1.4%</td></tr>
        <tr><td>$I_{rms}$</td><td>10 A</td><td>9.90 A</td><td>−1.0%</td></tr>
        <tr><td>$P$</td><td>2185 W</td><td>2131 W</td><td>−2.5%</td></tr>
        <tr><td>PF</td><td>0.950</td><td>0.949</td><td>−0.1%</td></tr>
      </tbody>
    </table>
    <div class="callout warning" style="margin-top: 18px">Circuit-level simulation plus numerical replication of firmware math—not a physical calibration result.</div>
  </div>
</div>

---

<div class="section-label">Appendix B · Edge ML cost</div>

# Asynchronous scoring decouples inference from ingestion

<div class="grid-2-wide">
  <div>
    <img class="img-frame no-shadow" style="max-height: 430px" src="./assets/fig4_async_decoupling.png" alt="Inline versus asynchronous edge ML latency">
  </div>
  <div>
    <h3>Before</h3>
    <p class="small">Per-reading synchronous `score_samples` added approximately 12 ms to telemetry latency.</p>
    <h3 style="margin-top: 20px">After</h3>
    <p class="small">A bounded micro-batch worker returned telemetry latency to rule-only levels.</p>
    <h3 style="margin-top: 20px">Trade-off</h3>
    <p class="small">The cost moved to approximately 49 ms enqueue-to-score delay, dominated by the 50 ms batch window.</p>
  </div>
</div>

---

class: diagram-slide

---

<div class="section-label">Appendix C · Gateway internals</div>

# Runtime component ownership

```mermaid {scale: 0.70, theme: 'neutral'}
flowchart TB
  MQTT["MQTTConsumerWorker"] --> ROUTE["Topic parser + dispatcher"]
  ROUTE --> VAL["ValidationService"]
  VAL -->|invalid| QUALITY["Data-quality repository"]
  VAL -->|valid telemetry| RULE["RuleEngine"]
  RULE --> STORE["StoragePolicyService"]
  RULE --> EVENTS["Event repository"]
  STORE --> READS["Reading repository"]
  RULE -.-> MLQ["MLScoringWorker"]
  MLQ --> MODEL["Isolation Forest"]
  MODEL --> PRED["Prediction repository"]
  EVENTS --> ALERT["AlertService"]
  ALERT --> OUTBOX["Alert outbox repository"]
  HEART["HeartbeatWorker"] --> EVENTS
  MAINT["Aggregation + retention worker"] --> SQL["Async SQL sessions"]
  QUALITY --> SQL
  READS --> SQL
  PRED --> SQL
  EVENTS --> SQL
  OUTBOX --> SQL
  SQL --> DB[("TimescaleDB")]
  OUTBOX --> DEST["Console / webhook / Slack"]
  READS -.-> HANDOFF["Cloud handoff service<br/>proposed"]
  EVENTS -.-> HANDOFF
  PRED -.-> HANDOFF
  HANDOFF -.-> CENTRAL[("Central cloud platform")]
```

---

<div class="section-label">Appendix D · Technology map</div>

# Implementation stack

| Layer          | Technology                            | Responsibility                                             |
| -------------- | ------------------------------------- | ---------------------------------------------------------- |
| Sensing design | ZMPT101B, SCT-013-030, KiCad, ngspice | Isolated voltage/current acquisition and analog validation |
| Firmware       | STM32F429ZI, LwIP, MQTT               | Sampling, electrical calculations, network publishing      |
| Messaging      | Eclipse Mosquitto                     | Publish/subscribe decoupling                               |
| Edge gateway   | FastAPI, Pydantic, SQLAlchemy async   | Validation, detection, APIs, metrics, workers              |
| Edge ML        | scikit-learn Isolation Forest         | Lightweight unsupervised anomaly scoring                   |
| Storage        | PostgreSQL + TimescaleDB + Alembic    | Time-series and operational evidence                       |
| Visualization  | Grafana                               | Five provisioned dashboards                                |
| Cloud target   | Central ingestion + data platform     | Cross-site aggregation, archive, analytics, and dashboards |
| Experiments    | Docker Compose, Bash/Python harnesses | Controlled A/B execution and evidence export               |

---

<div class="section-label">Appendix E · Selected references</div>

# Research foundations

<div class="reference-list">
  <p><strong>[1]</strong> D. A. Verde Romero et al., “An open source IoT edge-computing system for monitoring energy consumption in buildings,” <em>Results in Engineering</em>, vol. 21, 2024.</p>
  <p><strong>[2]</strong> R. K. Naha et al., “Fog Computing: Survey of Trends, Architectures, Requirements, and Research Directions,” 2018.</p>
  <p><strong>[3]</strong> R. B. Mofidul et al., “Real-Time Energy Data Acquisition, Anomaly Detection, and Monitoring System,” <em>Sensors</em>, vol. 22, no. 22, 2022.</p>
  <p><strong>[4]</strong> OASIS, “MQTT Version 5.0,” OASIS Standard, 2019.</p>
  <p><strong>[5]</strong> V. C. Gungor et al., “Survey of Smart Metering Communication Technologies,” <em>IEEE Communications Surveys & Tutorials</em>, 2011.</p>
  <p><strong>[6]</strong> A. Chatterjee and B. S. Ahmed, “IoT anomaly detection methods and applications: A survey,” <em>Internet of Things</em>, 2022.</p>
</div>

<div class="callout" style="margin-top: 18px">Complete citations and the source PDFs are maintained in the thesis literature-review workspace.</div>
