#include "sensor_sim.h"

#include <math.h>
#include <stdlib.h>

#include "stm32f4xx_hal.h" /* HAL_GetTick */

#define MAINS_FREQ_HZ   50.0f
#define BASE_VOLTAGE_V  220.0f   /* nominal RMS, matches simulator default */
#define TWO_PI          6.2831853f

/* Slowly varying load so consecutive telemetry points differ realistically. */
static float load_current_rms(uint32_t now_ms)
{
    /* 0.5–4 A drifting over ~10 min, plus small jitter. */
    float slow = 2.25f + 1.75f * sinf((float)now_ms * (TWO_PI / 600000.0f));
    float jitter = ((float)(rand() % 200) - 100.0f) / 1000.0f; /* ±0.1 A */
    return slow + jitter;
}

void sensor_read_sample(float *v_inst, float *i_inst)
{
    uint32_t now_ms = HAL_GetTick();
    float t = (float)now_ms / 1000.0f;
    float phase = TWO_PI * MAINS_FREQ_HZ * t;

    float v_rms = BASE_VOLTAGE_V + 3.0f * sinf((float)now_ms * (TWO_PI / 90000.0f));
    float i_rms = load_current_rms(now_ms);
    float pf_angle = 0.25f; /* ~cos 0.25 rad ≈ 0.97 lagging */

    *v_inst = v_rms * 1.41421356f * sinf(phase);
    *i_inst = i_rms * 1.41421356f * sinf(phase - pf_angle);
}

void sensor_measure(sensor_reading_t *out, uint32_t samples, uint32_t window_ms)
{
    float sum_v2 = 0.0f, sum_i2 = 0.0f, sum_p = 0.0f;
    uint32_t start = HAL_GetTick();

    for (uint32_t n = 0; n < samples; n++) {
        float v, i;
        sensor_read_sample(&v, &i);
        sum_v2 += v * v;
        sum_i2 += i * i;
        sum_p  += v * i;
        /* Spread samples across the window (busy-wait; fine at 1 Hz publish). */
        uint32_t target = start + (n * window_ms) / samples;
        while (HAL_GetTick() < target) { /* spin */ }
    }

    out->voltage_v = sqrtf(sum_v2 / (float)samples);
    out->current_a = sqrtf(sum_i2 / (float)samples);
    out->power_w   = sum_p / (float)samples;
    out->temperature_c = 30.0f + (float)(rand() % 100) / 20.0f; /* 30–35 °C */
}
