# STM32CubeIDE Project Checklist — Black Pill (STM32F411CEU6)

Create the project once in CubeIDE, then pull in `app/` and `config.h`. The
generated `main.c` only needs two lines in USER CODE sections, so regenerating
from the `.ioc` never clobbers application logic.

## 1. New project

- **File → New → STM32 Project**, part number **STM32F411CEU6** (Black Pill).
  Name it `blackpill-node` so it sits next to `app/`.

## 2. Clock (RCC)

- HSE: **Crystal/Ceramic Resonator** (Black Pill has a 25 MHz crystal).
- Clock config: set **HCLK = 96 MHz** (or 100 MHz). Note SYSCLK for timer math.

## 3. ADC1 — two channels, timer-triggered, DMA

- Enable **ADC1 IN0 (PA0)** and **ADC1 IN1 (PA1)**.
- Parameters:
  - Mode: **Scan Conversion = Enabled**, **Continuous = Disabled**.
  - **Number of Conversions = 2**; Rank 1 = **Channel 0**, Rank 2 = **Channel 1**
    (must match `ADC_CH_VOLTAGE`/`ADC_CH_CURRENT` in `config.h`).
  - **External Trigger Conversion = Timer 2 Trigger Out event**, rising edge.
  - Sampling time: **≥ 84 cycles** each (source impedance of the front-end).
- **DMA**: add ADC1 request, **Circular**, **Half Word**, Mem increment on.
- NVIC: enable the DMA stream global interrupt.

## 4. TIM2 — sample clock (SAMPLE_RATE_HZ = 3200 Hz)

- Clock Source: **Internal**.
- Set PSC/ARR so update rate = 3200 Hz. Example at 96 MHz APB1 timer clock:
  `PSC = 99`, `ARR = 299` → 96e6 / (100 * 300) = **3200 Hz**.
- **Trigger Event Selection (TRGO) = Update Event**.

## 5. USART1 — link to ESP-01 (115200 8N1)

- **PA9 = USART1_TX**, **PA10 = USART1_RX**, 115200 baud.

## 6. GPIO

- **PC13** as output (onboard LED) for a heartbeat, optional.

## 7. Generate + wire in the app

- Copy/link `config.h` and the whole `app/` folder into the project
  (Project → Properties → C/C++ General → Paths & Symbols → add `app` include).
- In generated `Core/Src/main.c`:
  - `/* USER CODE BEGIN Includes */` → `#include "node.h"`
  - `/* USER CODE BEGIN 2 */` → `node_setup(&hadc1, &htim2, &huart1);`
  - `/* USER CODE BEGIN 3 */` (in `while(1)`) → `node_loop();`
- In `Core/Src/stm32f4xx_it.c` (or wherever the HAL ADC callbacks live), route
  the DMA callbacks:

  ```c
  void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef *h){ adc_sampler_on_dma_half(); }
  void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *h)     { adc_sampler_on_dma_full(); }
  ```

  (add `#include "adc_sampler.h"`).

## 8. Build & flash

- Build → produces `blackpill-node.elf`.
- Flash via ST-Link (SWD: PA13/PA14) or DFU (BOOT0 jumper + USB).

## 9. Bring-up order (see PLAN.md §7)

1. LED blink + `esp01_publish` a status line, watch it on a USB-UART.
2. Feed a **6–12 V AC adapter** through the front-end; dump raw ADC to confirm
   clean sines before trusting RMS.
3. Verify `metrology_compute` output against a multimeter; tune `config.h`.
4. Only then move to 220 V (enclosed, MCB/RCD — see PLAN.md §6).
