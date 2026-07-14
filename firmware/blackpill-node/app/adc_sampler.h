#ifndef ADC_SAMPLER_H
#define ADC_SAMPLER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* TIM-triggered, DMA-driven capture of two ADC channels (voltage, current)
 * into a double buffer. One half fills while the other is processed.
 *
 * Wiring to the CubeIDE-generated project (see cubemx-checklist.md):
 *   - ADC1: 2 conversions, scan mode, ch order = {ADC_CH_VOLTAGE, ADC_CH_CURRENT}
 *   - external trigger = TIM2 TRGO at SAMPLE_RATE_HZ
 *   - DMA circular, half-word, length 2*WINDOW_SAMPLES
 *   - call adc_sampler_on_dma_half()/_full() from the DMA HT/TC callbacks. */

/* Start timer + ADC + DMA. Pass the CubeMX handles (void* to keep this header
 * HAL-free); the .c casts them. Returns false on HAL error. */
bool adc_sampler_start(void *hadc1, void *htim2);

/* True once a window (WINDOW_SAMPLES sample-pairs) is ready. Clears on read. */
bool adc_sampler_window_ready(void);

/* De-interleaved most-recent window. Buffers hold WINDOW_SAMPLES each and stay
 * valid until the next adc_sampler_window_ready() returns true. */
const uint16_t *adc_sampler_voltage(void);
const uint16_t *adc_sampler_current(void);
size_t adc_sampler_window_len(void);

/* DMA callbacks — wire these to HAL_ADC_ConvHalfCpltCallback / ..CpltCallback. */
void adc_sampler_on_dma_half(void);
void adc_sampler_on_dma_full(void);

#endif /* ADC_SAMPLER_H */
