#ifndef CONFIG_H
#define CONFIG_H

/* ------------------------------------------------------------------ *
 * Energy node configuration — STM32F411 "Black Pill".
 * One place for pins, sampling rate, calibration and broker settings.
 * ------------------------------------------------------------------ */

/* --- Identity ---------------------------------------------------- */
#define NODE_DEVICE_ID        "stm32_0001"   /* MQTT client / topic id */
#define NODE_FIRMWARE_VERSION "0.1.0"

/* --- Sampling ---------------------------------------------------- */
#define MAINS_FREQ_HZ         50u
#define SAMPLES_PER_CYCLE     64u             /* -> 3.2 kHz at 50 Hz    */
#define CYCLES_PER_WINDOW     10u             /* 200 ms compute window  */
#define SAMPLE_RATE_HZ        (MAINS_FREQ_HZ * SAMPLES_PER_CYCLE)
#define WINDOW_SAMPLES        (SAMPLES_PER_CYCLE * CYCLES_PER_WINDOW)
#define PUBLISH_PERIOD_MS     1000u           /* one telemetry msg / s  */

/* --- ADC channels (ADC1 scan order must match this) -------------- */
#define ADC_CH_VOLTAGE        0u              /* PA0 <- ZMPT101B        */
#define ADC_CH_CURRENT        1u              /* PA1 <- ACS712 / SCT013 */
#define ADC_FULL_SCALE_COUNTS 4095.0f         /* 12-bit                 */
#define ADC_VREF_V            3.3f

/* --- Calibration (tune against a multimeter, see PLAN.md §5) ------ *
 * *_SCALE converts DC-removed ADC counts to real-world units.
 * Start from theory, then trim empirically. Offsets are auto-removed
 * per window (mean subtraction), so leave them at the mid-rail guess. */
#define CAL_V_SCALE           0.3500f         /* counts -> volts        */
#define CAL_I_SCALE           0.0075f         /* counts -> amps (ACS712) */
#define CAL_V_OFFSET          2048.0f         /* mid-rail (auto-refined) */
#define CAL_I_OFFSET          2048.0f

/* --- MQTT (handled by the ESP-01; STM32 just emits JSON lines) ---- */
#define MQTT_BROKER_HOST      "192.168.0.10"
#define MQTT_BROKER_PORT      1883
#define MQTT_TOPIC_TELEMETRY  "energy/" NODE_DEVICE_ID "/telemetry"
#define MQTT_TOPIC_STATUS     "energy/" NODE_DEVICE_ID "/status"

#endif /* CONFIG_H */
