#ifndef METROLOGY_H
#define METROLOGY_H

#include <stddef.h>
#include <stdint.h>

/* Pure-C AC metrology: no HAL, no globals. Fed raw ADC samples, returns
 * calibrated RMS / power / power-factor. Host-testable (see test/). */

typedef struct {
    float v_scale;   /* DC-removed ADC counts -> volts */
    float i_scale;   /* DC-removed ADC counts -> amps  */
    float v_offset;  /* nominal mid-rail counts (refined per window) */
    float i_offset;
} calib_t;

typedef struct {
    float voltage_v;    /* Vrms  */
    float current_a;    /* Irms  */
    float power_w;      /* real power P = mean(v*i) */
    float apparent_va;  /* S = Vrms * Irms */
    float power_factor; /* P / S, 0 if S == 0 */
} power_metrics_t;

/* Compute metrics from one window of interleaved-free channel buffers.
 * v_raw / i_raw hold `n` 12-bit ADC samples each. The per-window DC offset
 * is measured from the data (offsets in `cal` are only a fallback when a
 * channel is flat). Safe for n == 0 (returns all zeros). */
void metrology_compute(const uint16_t *v_raw, const uint16_t *i_raw,
                       size_t n, const calib_t *cal, power_metrics_t *out);

#endif /* METROLOGY_H */
