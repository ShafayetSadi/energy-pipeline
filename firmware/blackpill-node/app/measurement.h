#ifndef MEASUREMENT_H
#define MEASUREMENT_H

/* Telemetry-facing reading, matching pipeline schema 1.0 fields. Populated
 * from power_metrics_t (metrology.h) plus the on-chip temperature sensor. */
typedef struct {
    float voltage_v;
    float current_a;
    float power_w;
    float temperature_c;
} sensor_reading_t;

#endif /* MEASUREMENT_H */
