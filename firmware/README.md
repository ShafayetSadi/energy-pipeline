# Energy Node Firmware — Real Hardware

STM32 firmware for the energy-monitoring IoT node. The node measures **real AC
mains** (voltage + current), computes the metrology on-device, and publishes the
same JSON schema/topics the pipeline already expects (Mosquitto → gateway →
TimescaleDB → Grafana → LSTM), so the cloud side is unchanged.

- **Node:** STM32F411 "Black Pill"
- **Voltage sensor:** ZMPT101B · **Current sensor:** ACS712-5A (primary),
  SCT-013-000 clamp (backup)
- **Uplink:** ESP-01 (ESP8266) as a UART→MQTT bridge

> See **[PLAN.md](PLAN.md)** for the full build plan, wiring, calibration and
> mains-safety procedure. **Validate on a 6–12 V AC adapter before touching
> 220 V.**

## Layout

```text
firmware/
  PLAN.md                full build plan (BOM, front-end, safety, milestones)
  README.md              this file
  blackpill-node/
    cubemx-checklist.md  STM32CubeIDE (F411) project setup
    config.h             pins, sampling rate, calibration, broker
    app/                 portable application code (pulled into the CubeIDE project)
      metrology.[ch]     pure-C RMS / power / PF (host-testable, no HAL)
      adc_sampler.[ch]   TIM+ADC+DMA double-buffer capture
      esp01_mqtt.[ch]    UART JSON-line bridge to the ESP-01
      telemetry.[ch]     JSON payload builder (pipeline schema 1.0)
      measurement.h      telemetry-facing reading struct
      node.[ch]          app glue: node_setup() / node_loop()
    test/                host unit tests for metrology (no hardware)
    esp01/               ESP8266 MQTT-bridge sketch (Arduino + PubSubClient)
  hardware/              analog front-end schematic + ngspice sims
```

## Verify the metrology core (no hardware)

```sh
make -C blackpill-node/test check
```

Builds `metrology.c` on the host and checks Vrms/Irms/power/PF against
synthesized resistive and 60°-lagging waveforms.

## On-hardware workflow

1. Create the CubeIDE project per `blackpill-node/cubemx-checklist.md`; pull in
   `config.h` + `app/`. Build → `blackpill-node.elf`.
2. Flash the Black Pill (ST-Link SWD or DFU).
3. Flash `blackpill-node/esp01/mqtt_bridge.ino` to the ESP-01 (edit Wi-Fi /
   broker at the top).
4. Bring up in order (LED/UART → low-voltage AC → calibrate → 220 V) as in
   **PLAN.md §7**.

## Note

Renode is gone: it cannot emulate the analog front-end, so there is no
simulator stand-in for the metrology path — the demo needs the physical board.
Report **measured** accuracy vs. a multimeter, not datasheet-ideal numbers.
