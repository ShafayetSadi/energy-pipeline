# STM32 Energy Node Firmware

STM32 firmware for the energy-monitoring IoT node, developed in **STM32CubeIDE**
and executed in the **Renode** emulator (no hardware required). The emulated
board's Ethernet is bridged to the host, so the firmware publishes real MQTT
traffic into the unmodified pipeline (Mosquitto → FastAPI gateway →
TimescaleDB → Grafana).

- Target board: **Nucleo-F429ZI** (STM32F429ZIT6, on-chip Ethernet MAC)
- Network stack: LwIP (CubeMX middleware) + its built-in MQTT client
- Payloads: identical schema/topics to `simulator/mqtt_publisher.py`, so the
  gateway cannot tell the node apart from a Python-simulated device — except
  that this one is real firmware with a real TCP/MQTT session (LWT, reconnects).

## Layout

```text
firmware/
  README.md            this file
  cubemx-checklist.md  step-by-step CubeMX/CubeIDE project configuration
  app/                 portable application code, copied/linked into the
                       CubeIDE-generated project (hardware-independent)
    sensor_sim.[ch]    synthetic waveform sampling + RMS/power computation
    telemetry.[ch]     JSON payload builders (telemetry + status)
    mqtt_app.[ch]      LwIP MQTT client wrapper: connect, LWT, publish loop
  hardware/            analog front-end: full device schematic + ngspice
                       simulation of both sensor channels (see its README)
  renode/
    nucleo_f429zi.resc Renode script: load ELF, bridge Ethernet to host TAP
    setup-tap.sh       one-time host TAP interface setup (needs sudo)
```

The CubeIDE-generated project itself (HAL, startup code, `.ioc`) is created by
you following `cubemx-checklist.md`; it lives in `firmware/node-f429zi/` and
its generated sources are not hand-edited except the marked USER CODE sections.

## Workflow

1. Follow `cubemx-checklist.md` to create the CubeIDE project and pull in
   `app/`. Build → produces `node-f429zi.elf`.
2. One-time per boot: `sudo ./renode/setup-tap.sh` (creates `tap-stm32`,
   192.168.100.1/24, and un-manages it from NetworkManager).
3. Ensure Mosquitto is listening where the firmware expects it (see
   `mqtt_app.h`: default broker `192.168.100.1:18831`, i.e. the host end of
   the TAP bridge and the docker-compose host port).
4. `./renode/run.sh` — patches `g_epoch_seed` with the current unix time
   (harness stand-in for SNTP, so gateway timestamp validation passes) and
   boots the ELF. UART3 shows bring-up and per-publish logs.
5. Watch the gateway/Grafana: device `stm32_0001` appears like any other.

## Renode workarounds (documented for the thesis)

Renode's `SynopsysEthernetMAC` model diverges from real F4 silicon in two
ways this firmware compensates for (both changes live in USER CODE sections):

1. **ETH interrupt storm** — the model's IRQ/status semantics don't match the
   ST HAL's clearing sequence, so the ETH NVIC interrupt is kept disabled
   (`ethernetif.c`, `ETH_MspInit`); Rx runs in polling mode as configured.
2. **Frame-queue latch** — after delivering one frame the model queues all
   further RX until the DMA status register is acknowledged (normally done by
   the ISR). The main loop writes `ETH->DMASR = NIS|RS` each iteration
   (`main.c`), which is harmless on real hardware.

Timestamps: the emulated RTC has no host-clock mode, so `renode/run.sh`
patches the current epoch into flash at load time (`g_epoch_seed` in
`telemetry.c`). On hardware the seed is 0 and the RTC/SNTP path applies.

## Sensor model (honesty note)

Renode stubs the ADC, so the analog front-end (ZMPT101B voltage transformer,
SCT-013 CT, dividers) is **not** simulated. Instead `sensor_sim.c` generates
per-sample 50 Hz voltage/current waveforms and the firmware runs the same
sampling → RMS → power computation it would run on real ADC data. On hardware,
only `sensor_read_sample()` changes (swap synthetic generator for ADC+DMA).

The analog front-end itself (ZMPT101B + SCT-013 circuits) is designed and
validated separately at circuit level in `hardware/` (ngspice), and the
simulated ADC waveforms are verified through the firmware's RMS/power math
(`hardware/spice/verify_chain.py`, errors < 2.5 % with design-value
calibration). State this explicitly in the thesis: firmware logic and network
behavior are validated in emulation, the analog design at circuit level in
SPICE; a physically integrated build and metrology calibration are future
hardware work.

## Milestones

1. Blink + UART printf in Renode (toolchain sanity).
2. LwIP up, static IP on TAP bridge, ping from host.
3. MQTT connect + LWT status (`energy/stm32_0001/status`).
4. Telemetry publishing at 1 Hz with RMS values from `sensor_sim`.
5. (Stretch) real Nucleo-F429ZI board on the LAN — same binary, DHCP instead
   of static IP.
