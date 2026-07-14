#include "adc_sampler.h"

#include "stm32f4xx_hal.h"

#include "../config.h"

/* ADC scans {voltage, current} each trigger, so DMA sees interleaved pairs.
 * Two windows back-to-back => ping-pong via the DMA half/complete interrupts. */
#define PAIRS        WINDOW_SAMPLES          /* pairs per window          */
#define DMA_LEN      (2u * 2u * PAIRS)       /* 2 windows * 2 channels    */

static uint16_t dma_buf[DMA_LEN];            /* [v,i,v,i,...] two windows  */
static uint16_t win_v[PAIRS];
static uint16_t win_i[PAIRS];
static volatile bool window_ready;

static void deinterleave(const uint16_t *half)
{
    for (size_t k = 0; k < PAIRS; k++) {
        win_v[k] = half[2u * k + ADC_CH_VOLTAGE];
        win_i[k] = half[2u * k + ADC_CH_CURRENT];
    }
    window_ready = true;
}

bool adc_sampler_start(void *hadc1, void *htim2)
{
    ADC_HandleTypeDef *adc = (ADC_HandleTypeDef *)hadc1;
    TIM_HandleTypeDef *tim = (TIM_HandleTypeDef *)htim2;

    window_ready = false;
    if (HAL_ADC_Start_DMA(adc, (uint32_t *)dma_buf, DMA_LEN) != HAL_OK)
        return false;
    return HAL_TIM_Base_Start(tim) == HAL_OK;
}

bool adc_sampler_window_ready(void)
{
    bool r = window_ready;
    window_ready = false;
    return r;
}

const uint16_t *adc_sampler_voltage(void) { return win_v; }
const uint16_t *adc_sampler_current(void) { return win_i; }
size_t adc_sampler_window_len(void)       { return PAIRS; }

/* First window filled (samples 0 .. 2*PAIRS-1). */
void adc_sampler_on_dma_half(void) { deinterleave(&dma_buf[0]); }

/* Second window filled (samples 2*PAIRS .. DMA_LEN-1). */
void adc_sampler_on_dma_full(void) { deinterleave(&dma_buf[2u * PAIRS]); }
