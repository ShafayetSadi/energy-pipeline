#ifndef SENSOR_SIM_H
#define SENSOR_SIM_H

#include <stdint.h>

/* One computed measurement window (electrical quantities over N mains cycles). */
typedef struct {
    float voltage_v;      /* RMS */
    float current_a;      /* RMS */
    float power_w;        /* real power (mean of v*i samples) */
    float temperature_c;
} sensor_reading_t;

/* Return one instantaneous (voltage, current) sample pair.
 * Simulation build: synthesized 50 Hz waveforms with load drift and noise.
 * Hardware build: replace body with ADC+DMA reads scaled by the front-end
 * constants (ZMPT101B / SCT-013 burden + divider). The rest of the firmware
 * is unchanged. */
void sensor_read_sample(float *v_inst, float *i_inst);

/* Sample `samples` points over `window_ms` and compute RMS/real power. */
void sensor_measure(sensor_reading_t *out, uint32_t samples, uint32_t window_ms);

#endif /* SENSOR_SIM_H */
