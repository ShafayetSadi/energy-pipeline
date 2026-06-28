# Chapter 6: Results and Discussion

## 6.1 Latency Results

Present measured latency results and explain what they indicate about edge responsiveness.

## 6.2 Throughput Results

Show throughput behavior under the selected test scenarios and discuss system stability.

## 6.3 Validation and Data Quality Results

Present validation outcomes, invalid payload handling, and data-quality log evidence.

## 6.4 Event Detection Results

Present the event detection outcomes, rule-trigger behavior, and any false positives or missed cases.

## 6.5 Dashboard and Alerting Results

Discuss the quality of observability, dashboard usefulness, and how alerts support system monitoring.

## 6.6 Comparison with Related Work

Relate your findings back to the literature review and explain similarities, improvements, or remaining gaps.

## 6.7 Limitations

State technical, experimental, and methodological limitations honestly.

---

## Suggested result tables

### Latency comparison

| Scenario | Baseline | Proposed | Observation |
| -------- | -------- | -------- | ----------- |
|          |          |          |             |

### Throughput comparison

| Scenario | Baseline | Proposed | Observation |
| -------- | -------- | -------- | ----------- |
|          |          |          |             |

### Event detection comparison

| Scenario | Expected Event | Observed Count | Observation |
| -------- | -------- | -------- | --------- |
|          |          |          |           |

---

## Notes / Evidence to collect

- exported report tables
- screenshots of dashboards
- event examples
- discussion notes connecting results to objectives

---

## Migrated seed notes (draft/reference — verify before final use)

- Storage reduction is no longer a core measured thesis claim. Keep selective retention, downsampling, and event-only long-term storage as future work unless a separate controlled experiment is added.
- Another working claim is that event detection latency is bounded by MQTT round-trip plus rule evaluation overhead.
- Earlier notes mention sub-50ms behavior in test scenarios, but this must be verified against exported results before being stated in the final thesis.
