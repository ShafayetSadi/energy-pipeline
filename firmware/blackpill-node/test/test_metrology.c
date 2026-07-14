/* Host unit tests for the pure-C metrology core. No hardware, no HAL.
 * Build & run:  make -C firmware/blackpill-node/test  */
#include "../app/metrology.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N                640    /* 10 cycles * 64 samples */
#define MAINS_PER_WINDOW 10      /* whole cycles in the window */
#define MIDRAIL          2048.0f
#define TWO_PI           6.28318530718f

static int failures;

static void check(const char *name, float got, float want, float tol)
{
    float err = fabsf(got - want);
    int ok = err <= tol;
    printf("  [%s] %-14s got=%.4f want=%.4f (tol=%.4f)\n",
           ok ? "PASS" : "FAIL", name, got, want, tol);
    if (!ok) failures++;
}

/* Synthesize one window of ADC counts for a sinusoid at the given RMS
 * (real-world units) and phase, using the inverse of the calibration scale. */
static void synth(uint16_t *buf, float rms_units, float scale,
                  float phase, float bias)
{
    float amp_counts = (rms_units / scale) * 1.41421356f; /* peak in counts */
    for (int k = 0; k < N; k++) {
        float ph = TWO_PI * (float)MAINS_PER_WINDOW * (float)k / (float)N + phase;
        float c = bias + amp_counts * sinf(ph);
        if (c < 0) c = 0;
        if (c > 4095) c = 4095;
        buf[k] = (uint16_t)(c + 0.5f);
    }
}

int main(void)
{
    static uint16_t v[N], i[N];
    calib_t cal = { .v_scale = 0.35f, .i_scale = 0.0075f,
                    .v_offset = MIDRAIL, .i_offset = MIDRAIL };
    power_metrics_t m;

    /* Case 1: resistive load, PF = 1. */
    synth(v, 230.0f, cal.v_scale, 0.0f, MIDRAIL);
    synth(i, 5.0f,   cal.i_scale, 0.0f, MIDRAIL);
    metrology_compute(v, i, N, &cal, &m);
    puts("Case 1: 230 V, 5 A, resistive");
    check("vrms", m.voltage_v, 230.0f, 2.0f);
    check("irms", m.current_a, 5.0f, 0.1f);
    check("power", m.power_w, 1150.0f, 25.0f);
    check("pf", m.power_factor, 1.0f, 0.02f);

    /* Case 2: 60 deg lagging, PF = cos60 = 0.5. */
    synth(v, 230.0f, cal.v_scale, 0.0f, MIDRAIL);
    synth(i, 5.0f,   cal.i_scale, -TWO_PI / 6.0f, MIDRAIL);
    metrology_compute(v, i, N, &cal, &m);
    puts("Case 2: 60 deg lagging");
    check("pf", m.power_factor, 0.5f, 0.03f);
    check("power", m.power_w, 575.0f, 30.0f);

    /* Case 3: empty window is safe. */
    metrology_compute(v, i, 0, &cal, &m);
    puts("Case 3: n=0 guard");
    check("vrms", m.voltage_v, 0.0f, 0.0f);

    printf("\n%s (%d failure%s)\n", failures ? "FAILED" : "OK",
           failures, failures == 1 ? "" : "s");
    return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
