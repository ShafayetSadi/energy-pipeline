# Chapter 7: Conclusion and Future Work

## 7.1 Summary

Summarize the problem, approach, implementation, and findings of the thesis.

## 7.2 Contributions

List the concrete contributions made by the project and thesis.

Possible contribution areas:

- edge-based smart energy monitoring architecture
- configurable rule-driven event detection
- time-series observability pipeline
- baseline vs proposed evaluation
- future ML extension points

## 7.3 Limitations

Restate the most important practical and research limitations that affect interpretation or deployment.

## 7.4 Future AI/ML Extensions

Describe realistic next steps such as anomaly detection, load forecasting, predictive maintenance, or adaptive rule tuning.

## 7.5 Future Storage Optimization

Discuss selective raw-reading retention, downsampling, event-first long-term
storage, and database-size experiments as future work. The current thesis should
not claim measured storage reduction because the evaluated configuration stores
raw readings in both baseline and proposed modes.

---

## Final checklist

- answer all research questions directly
- restate contributions clearly
- keep claims aligned with measured evidence
- distinguish completed work from future work

---

## Migrated seed notes (draft/reference)

### Clearly out of scope

- real AI/ML anomaly detection in the current version
- TLS-secured MQTT and per-device credentials
- production-grade electrical safety certification
- cloud / Kubernetes deployment

### Future work hooks already present in the project

- `model_predictions` table for future prediction or anomaly modules
- webhook-based alerting can be extended to Slack or email
- `reload()` support and DB-backed rule definitions can support future per-rule UI management
