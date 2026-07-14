#include "metrology.h"

#include <math.h>

void metrology_compute(const uint16_t *v_raw, const uint16_t *i_raw,
                       size_t n, const calib_t *cal, power_metrics_t *out)
{
    if (n == 0) {
        out->voltage_v = out->current_a = out->power_w = 0.0f;
        out->apparent_va = out->power_factor = 0.0f;
        return;
    }

    /* Pass 1: per-window DC offset from the actual samples. Removing the
     * measured mean rejects the sensor bias drift better than a fixed guess. */
    double sum_v = 0.0, sum_i = 0.0;
    for (size_t k = 0; k < n; k++) {
        sum_v += v_raw[k];
        sum_i += i_raw[k];
    }
    float v_dc = (float)(sum_v / (double)n);
    float i_dc = (float)(sum_i / (double)n);
    (void)cal->v_offset; /* fallback only; measured mean is authoritative */
    (void)cal->i_offset;

    /* Pass 2: sums of squares and instantaneous power on centered samples. */
    double sq_v = 0.0, sq_i = 0.0, prod = 0.0;
    for (size_t k = 0; k < n; k++) {
        float v = (float)v_raw[k] - v_dc;
        float i = (float)i_raw[k] - i_dc;
        sq_v += (double)v * v;
        sq_i += (double)i * i;
        prod += (double)v * i;
    }

    float vrms_counts = sqrtf((float)(sq_v / (double)n));
    float irms_counts = sqrtf((float)(sq_i / (double)n));
    float p_counts    = (float)(prod / (double)n);

    out->voltage_v   = vrms_counts * cal->v_scale;
    out->current_a   = irms_counts * cal->i_scale;
    out->power_w     = p_counts * cal->v_scale * cal->i_scale;
    out->apparent_va = out->voltage_v * out->current_a;
    out->power_factor =
        out->apparent_va > 1e-6f ? out->power_w / out->apparent_va : 0.0f;
}
