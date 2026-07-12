# CubeMX / STM32CubeIDE project checklist — Nucleo-F429ZI

Create the project once by hand; this checklist pins every setting that
matters. Project name: `node-f429zi`, location: `firmware/`.

> **STM32CubeIDE 2.0 note:** CubeMX is no longer built into the IDE. Install
> **standalone STM32CubeMX** from st.com, create/configure the project there,
> generate code with Toolchain/IDE = STM32CubeIDE, then import into the IDE
> (File → Import → General → Existing Projects into Workspace).
> Never open the `.ioc` from inside CubeIDE 2.0 — it can silently clobber
> project settings (linked folders, language, linker script). Always edit the
> `.ioc` in standalone CubeMX and regenerate.

## 1. New project (standalone STM32CubeMX)

- File → New Project → **Board Selector** → `NUCLEO-F429ZI`.
- "Initialize all peripherals with their default Mode?" → **Yes**.
- Project Manager tab: Project Name `node-f429zi`, Location
  `/data/Projects/energy-pipeline/firmware/`,
  **Toolchain/IDE = STM32CubeIDE**. Then **Generate Code**.

## 2. Clocks (RCC / Clock Configuration tab)

- HSE: BYPASS (ST-LINK 8 MHz on the real board; Renode doesn't care).
- SYSCLK = 168 MHz via PLL (default board setup is fine). HCLK 168 MHz.

## 3. Ethernet (Connectivity → ETH)

- Mode: **RMII** (board default; PHY = LAN8742).
- Leave default PHY address (0). NVIC: enable Ethernet global interrupt.
  (The firmware immediately disables it again in the `ETH_MspInit` USER CODE
  section — required under Renode, see README "Renode workarounds".)

## 4. LwIP (Middleware → LWIP)

- Enabled. **DHCP: Disabled** — use static IP for the Renode TAP bridge:
  - IP: `192.168.100.2`, mask `255.255.255.0`, gateway `192.168.100.1`.
  - (For a real board on your LAN later, flip DHCP on; nothing else changes.)
- Key options (Key Options tab):
  - `LWIP_MQTT` is not a CubeMX toggle — the MQTT app sources ship with LwIP;
    add `Middlewares/Third_Party/LwIP/src/apps/mqtt/mqtt.c` to the build if
    the generator didn't (Project Properties → C/C++ General → Paths).
  - `MEM_SIZE` ≥ 16 KB (default 10x1524 heap is fine for 1 Hz JSON).
  - `LWIP_SNTP`: optional; without it firmware sends `uptime_ms`-derived
    timestamps and the gateway's received-time is authoritative (see
    `telemetry.c` note).

## 5. RTOS

- **None** (bare-metal + LwIP raw/callback API keeps the Renode story simple;
  `MX_LWIP_Process()` polled in the main loop). FreeRTOS is optional later.

## 6. Console UART

- USART3 (connected to ST-LINK VCP on the real board, and to the Renode
  UART analyzer): 115200 8N1, asynchronous.
- Retarget `printf`: add `int __io_putchar(int ch)` calling
  `HAL_UART_Transmit(&huart3, ...)` in `main.c` USER CODE.

## 7. Timebase

- SysTick default (1 ms). `HAL_GetTick()` is used by `sensor_sim`/`mqtt_app`.

## 8. Pull in the application code

- Project Properties → C/C++ General → Paths and Symbols → add
  `../../app` as source folder and include path (or copy `app/*.[ch]` into
  `Core/Src` / `Core/Inc` if you prefer CubeIDE-managed files).
- In `main.c` USER CODE sections:

```c
/* USER CODE BEGIN Includes */
#include "mqtt_app.h"
/* USER CODE END Includes */

/* USER CODE BEGIN 2 */   // after MX_LWIP_Init()
mqtt_app_init();
/* USER CODE END 2 */

/* USER CODE BEGIN WHILE */
while (1) {
  MX_LWIP_Process();
  mqtt_app_poll();
/* USER CODE END WHILE */
```

## 9. Build

- Build (Release or Debug). Artifact: `node-f429zi/Debug/node-f429zi.elf`
  — this is what `renode/nucleo_f429zi.resc` loads.
