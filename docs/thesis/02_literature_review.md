# Chapter 2: Literature Review

## 2.1 Smart Energy Monitoring Systems

Smart energy monitoring systems are designed to measure electrical parameters
such as voltage, current, power, and energy consumption, then communicate
those measurements to users or operators. A typical system contains a sensing
layer, communication layer, processing layer, storage layer, and visualization
layer. The sensing layer measures electrical behavior. The communication layer
transmits measurements. The processing layer validates or analyzes data. The
storage layer keeps historical records. The visualization layer presents
readings, events, and trends through dashboards or applications.

Smart meters and energy monitoring systems are important because they provide
near-real-time visibility into consumption and power quality. Smart metering
literature commonly emphasizes two-way communication, remote monitoring, and
fine-grained measurement as improvements over manual meter reading or
periodic billing-only systems [1]. Low-cost IoT energy monitoring prototypes
also show that microcontrollers and wireless communication can reduce manual
effort and provide users with more immediate energy-consumption feedback [2].

However, many basic monitoring systems focus on collecting and displaying
readings. They may not measure the cost of adding local event intelligence, or
compare a raw telemetry pipeline against an edge-processing pipeline. This
thesis follows the layered smart energy monitoring model but focuses on the
edge gateway layer, where validation, event classification, and metrics can be
performed before long-term storage.

## 2.2 IoT-Based Energy Data Acquisition

IoT-based energy acquisition systems commonly use microcontrollers, electrical
sensors, and wireless modules. The device samples voltage and current,
calculates power, packages the values into a payload, and transmits the
payload through a communication protocol. Low-cost systems often use Arduino,
ESP, STM32, optical meter pulse sensors, current transformers, or voltage
sensing circuits depending on the required accuracy and safety constraints
[2].

In a practical deployment, hardware design must consider sensor calibration,
electrical isolation, sampling frequency, firmware timing, network
reliability, and power supply stability. These concerns are important for
field deployment, but they are different from the gateway evaluation performed
in this thesis. The current evaluation uses a simulator to produce repeatable
MQTT telemetry. This allows the software pipeline to be tested under
controlled high-throughput and anomaly scenarios without mixing hardware
measurement error into the gateway analysis.

The simulator-based approach is appropriate for evaluating ingestion latency,
rule-processing overhead, validation behavior, and dashboard observability.
Real STM32/ESP hardware validation remains future work.

## 2.3 MQTT in IoT Communication

MQTT is widely used in IoT systems because it is a lightweight
publish/subscribe protocol. MQTT.org describes it as an OASIS standard
messaging protocol for IoT, designed for remote devices with small code
footprints and limited bandwidth [3]. Its publish/subscribe model separates
publishers from subscribers through a broker. Devices publish messages to
topics, and interested consumers subscribe to topic filters.

This model is suitable for distributed energy monitoring. Energy nodes do not
need to know the address or implementation details of the gateway. They only
publish telemetry to a topic. The gateway subscribes to the relevant topic
pattern and processes messages as they arrive. MQTT also supports
bidirectional communication, quality-of-service levels, persistent sessions,
and TLS-based security options [3], [4].

Research on MQTT-based wireless sensor nodes also highlights its simplicity,
low overhead, and suitability for constrained networked devices compared with
heavier request/response protocols [5]. Other MQTT research explores broker
extensions and distributed broker architectures, showing that MQTT is common
enough in IoT systems that researchers study how to add filtering,
aggregation, or edge-oriented broker behavior [6], [7].

This thesis uses the following MQTT topic structure:

```text
energy/{device_id}/telemetry
energy/{device_id}/status
energy/{device_id}/events
```

The edge gateway subscribes to:

```text
energy/+/telemetry
energy/+/status
energy/+/events
```

This topic design separates measurements, device status, and events while
remaining simple enough for low-cost devices or simulators.

## 2.4 Edge and Fog Computing for IoT Monitoring

Cloud-only IoT architectures can centralize storage and processing, but they
may introduce latency, bandwidth cost, and dependency on wide-area network
availability. Edge and fog computing address this by placing computation and
storage closer to the data source. Surveys of fog computing describe fog
nodes as intermediate computation and storage resources between IoT devices
and cloud systems, useful for latency-sensitive applications [8]. Edge/fog
computing literature also notes that processing IoT data closer to devices
can reduce cloud dependence and support faster application response [8], [9].

For smart energy monitoring, this means a gateway can validate and classify
telemetry before data is sent to long-term storage or cloud systems. This is
important because abnormal conditions such as overload, under-voltage, or
device silence may require timely attention. Waiting until a later dashboard
query may delay awareness.

This thesis applies the edge-computing idea through a FastAPI gateway. The
gateway runs near the MQTT broker and database in the local stack. It consumes
messages, validates payloads, applies rule-based detection, stores events,
and exposes metrics. The evaluation then measures the latency overhead of
that edge processing compared with a simpler baseline ingestion path.

## 2.5 Time-Series Storage and Observability

Energy readings are naturally time-series data. Each reading is meaningful
because of its timestamp, device ID, and measured values. Common queries
include latest value per device, readings over a time range, aggregated power
over time, event counts by minute, validation failures, and gateway latency
history. These query patterns fit a time-series storage model.

TimescaleDB extends PostgreSQL for time-series workloads. Its documentation
describes hypertables as PostgreSQL tables that automatically partition
time-series data by time and optionally by other dimensions, allowing queries
to target relevant chunks instead of scanning an entire table [10]. This is
appropriate for energy monitoring because recent readings and time-window
queries are central to the dashboard and evaluation workflow.

Grafana is commonly used for observability dashboards. The Grafana
PostgreSQL datasource supports time-series queries, table queries, template
variables, annotations, alerting, and built-in time filtering/grouping macros
[11]. This makes it suitable for visualizing readings, events, validation
failures, and gateway metrics stored in PostgreSQL/TimescaleDB.

In this project, TimescaleDB stores `energy_readings`, `events`,
`data_quality_logs`, `device_status_history`, and `system_metrics`. Grafana
then visualizes these tables through energy overview, device detail, event
timeline, system observability, and thesis evaluation dashboards.

## 2.6 Rule-Based Event Detection

Monitoring systems often begin with rule-based event detection. A rule-based
system defines abnormal conditions using thresholds, comparisons, or
state-change logic. Examples include voltage below a lower bound, current
above an overload threshold, or power increasing by a percentage within a
short window.

Rule-based detection has several advantages for a thesis prototype. It is
explainable, deterministic, simple to configure, and fast to evaluate at the
edge. It is also easier to defend in an experimental comparison because each
event can be traced back to a specific condition and threshold.

Rule-based detection also has limitations. Fixed thresholds may not adapt to
seasonal behavior, different household patterns, equipment age, or changing
loads. More advanced anomaly detection literature often studies statistical
or machine-learning methods for IoT and energy systems [12], [13]. Those
methods can be useful, but they require training data, model evaluation, and
careful treatment of false positives and false negatives.

For this thesis, rule-based detection is appropriate because the objective is
to evaluate the architecture and processing overhead of an event-driven edge
gateway. Machine-learning anomaly detection remains future work.

## 2.7 Review of Related Work

The related literature and technical references show that smart energy
monitoring, MQTT-based communication, edge/fog computing, time-series
storage, and anomaly detection are established research and engineering
areas. The gap is not the existence of any one component. The gap is the
measured integration of these components into a baseline-versus-proposed
edge-gateway evaluation.

| Work | Focus | Technology | Strengths | Limitations | Relation to this thesis |
| --- | --- | --- | --- | --- | --- |
| Smart meter and AMI literature [1] | Remote energy measurement and two-way metering communication | Smart meters, AMI networks | Establishes the importance of near-real-time energy visibility | Utility-scale systems are broader than this prototype | Provides background for energy monitoring requirements |
| Islam et al. low-cost smart energy meter [2] | Low-cost IoT energy monitoring | Arduino, optical sensor, Android app | Shows practical low-cost monitoring and user feedback | Focuses more on meter reading/application than edge-gateway evaluation | Motivates low-cost IoT monitoring but leaves gateway comparison open |
| MQTT official/OASIS material [3], [4] | Lightweight IoT messaging | MQTT broker, clients, topics, QoS | Supports constrained devices and publish/subscribe decoupling | Security and ordering require careful system design | Justifies MQTT topic-based communication in this project |
| MQTT wireless sensor node work [5] | MQTT for sensor networks | MQTT, Wi-Fi, embedded nodes | Shows MQTT suitability for simple networked sensing | Not specific to energy event detection | Supports the communication choice |
| MQTT+ and distributed MQTT broker research [6], [7] | Broker-side filtering, aggregation, and distributed MQTT | MQTT extensions and broker architectures | Shows interest in processing closer to MQTT infrastructure | Changes or extends broker behavior rather than gateway-layer processing | Reinforces the value of edge-side processing near MQTT data flow |
| Fog computing survey [8] | Processing between IoT devices and cloud | Fog nodes, edge resources | Explains latency-aware local computation for IoT | Broad survey, not energy-specific | Supports the edge-gateway architectural decision |
| Edge/fog/cloud overview [9] | Distributed computation for IoT | Edge, fog, cloud | Discusses latency and bandwidth motivation | Broad application scope | Frames why local gateway processing is useful |
| TimescaleDB documentation [10] | Time-series storage | PostgreSQL hypertables and chunks | Supports time-window queries and partitioning | Storage optimization must still be designed per workload | Justifies TimescaleDB for readings/events/metrics |
| Grafana PostgreSQL documentation [11] | Dashboard observability | PostgreSQL datasource, macros, annotations | Supports time-series visualization and table dashboards | Dashboard quality depends on query design | Justifies Grafana for thesis evidence and operational visibility |
| IoT anomaly detection survey material [12] | Anomaly detection methods for IoT | Statistical and ML methods | Shows importance of anomaly detection in IoT systems | ML methods require datasets and model evaluation | Positions ML as future work beyond rule-based detection |
| IoT smart energy management review [13] | Smart energy analytics and energy disaggregation | IoT networks, energy management, algorithms | Shows broader direction toward intelligent analysis | Focuses on advanced analytics beyond this implementation | Supports future ML/forecasting extension direction |

## 2.8 Research Gap

Existing work shows that smart energy monitoring systems can collect and
display measurements, MQTT can support lightweight IoT messaging, edge/fog
computing can reduce cloud dependence, time-series databases can support
time-window queries, and anomaly detection is important for IoT systems.
However, many systems do not provide a measured comparison between a raw
telemetry ingestion pipeline and an event-driven edge gateway using latency,
throughput, validation behavior, event-detection counts, and dashboard
observability evidence.

This thesis responds to that gap by implementing and evaluating a complete
edge-gateway pipeline:

1. MQTT topic-based telemetry, status, and event ingestion.
2. Payload validation and data-quality logging.
3. Rule-based event detection at the gateway.
4. PostgreSQL/TimescaleDB storage for readings, events, validation logs, and metrics.
5. Grafana dashboards for operational and thesis evidence.
6. A clean baseline-versus-proposed high-throughput comparison.
7. A separate proposed-mode anomaly detection experiment.

The contribution is therefore not only a smart meter, not only a dashboard,
and not an ML anomaly detector. The contribution is a measured edge-gateway
architecture for smart energy monitoring, showing that rule-based event
intelligence can be added with low latency overhead.

## References

[1] V. C. Gungor et al., "Survey of Smart Metering Communication Technologies," IEEE Communications Surveys & Tutorials, 2011.

[2] M. R. Islam, S. Sarker, M. S. Mazumder, and M. R. Ranim, "An IoT based Real-time Low Cost Smart Energy Meter Monitoring System using Android Application," arXiv:2001.10350, 2020.

[3] MQTT.org, "MQTT: The Standard for IoT Messaging." https://mqtt.org/

[4] OASIS, "MQTT Version 5.0," OASIS Standard, 2019. https://docs.oasis-open.org/mqtt/mqtt/v5.0/

[5] Z. Shao, M. Huang, D. Wu, X. Zhang, and A. Huang, "Design of a Simplified Wireless Sensor Network Node based on MQTT Protocol," arXiv:1906.10540, 2019.

[6] R. Giambona, A. E. C. Redondi, and M. Cesana, "MQTT+: Enhanced Syntax and Broker Functionalities for Data Filtering, Processing and Aggregation," arXiv:1810.00773, 2018.

[7] E. Longo, A. E. C. Redondi, M. Cesana, A. Arcia-Moret, and P. Manzoni, "MQTT-ST: a Spanning Tree Protocol for Distributed MQTT Brokers," arXiv:1911.07622, 2019.

[8] R. K. Naha et al., "Fog Computing: Survey of Trends, Architectures, Requirements, and Research Directions," arXiv:1807.00976, 2018.

[9] T. Vo, P. Dave, G. Bajpai, and R. Kashef, "Edge, Fog, and Cloud Computing: An Overview on Challenges and Applications," arXiv:2211.01863, 2022.

[10] Tiger Data, "Hypertables," TimescaleDB documentation. https://www.tigerdata.com/docs/use-timescale/latest/hypertables

[11] Grafana Labs, "PostgreSQL data source," Grafana documentation. https://grafana.com/docs/grafana/latest/datasources/postgres/

[12] A. Chatterjee and B. S. Ahmed, "IoT anomaly detection methods and applications: A survey," Internet of Things, 2022.

[13] G. Huang, A. Anwar, S. W. Loke, A. Zaslavsky, and J. Choi, "IoT-based Analysis for Smart Energy Management," arXiv:2311.18643, 2023.
