#include "node.h"

#include "stm32f4xx_hal.h"

#include "../config.h"
#include "adc_sampler.h"
#include "esp01_mqtt.h"
#include "metrology.h"
#include "telemetry.h"

static const calib_t g_cal = {
    .v_scale  = CAL_V_SCALE,
    .i_scale  = CAL_I_SCALE,
    .v_offset = CAL_V_OFFSET,
    .i_offset = CAL_I_OFFSET,
};

/* Accumulate metrics across windows, publish once per PUBLISH_PERIOD_MS. */
static uint32_t last_publish_ms;
static uint32_t seq;

/* Running average of windows within a publish period. */
static power_metrics_t acc;
static uint32_t acc_n;

void node_setup(void *hadc1, void *htim2, void *huart1)
{
    esp01_init(huart1);
    adc_sampler_start(hadc1, htim2);
    esp01_publish(MQTT_TOPIC_STATUS, "{\"schema_version\":\"1.0\","
                  "\"device_id\":\"" NODE_DEVICE_ID "\",\"status\":\"online\"}");
    last_publish_ms = HAL_GetTick();
}

static void accumulate(void)
{
    power_metrics_t m;
    metrology_compute(adc_sampler_voltage(), adc_sampler_current(),
                      adc_sampler_window_len(), &g_cal, &m);
    acc.voltage_v   += m.voltage_v;
    acc.current_a   += m.current_a;
    acc.power_w     += m.power_w;
    acc.power_factor += m.power_factor;
    acc_n++;
}

static void publish(void)
{
    sensor_reading_t r = {0};
    if (acc_n > 0) {
        r.voltage_v = acc.voltage_v / (float)acc_n;
        r.current_a = acc.current_a / (float)acc_n;
        r.power_w   = acc.power_w   / (float)acc_n;
    }
    r.temperature_c = 0.0f; /* TODO: read on-chip temp sensor (ADC ch 16) */

    char json[256];
    telemetry_json(json, sizeof json, NODE_DEVICE_ID, &r, seq++);
    esp01_publish(MQTT_TOPIC_TELEMETRY, json);

    acc = (power_metrics_t){0};
    acc_n = 0;
}

void node_loop(void)
{
    if (adc_sampler_window_ready())
        accumulate();

    if ((uint32_t)(HAL_GetTick() - last_publish_ms) >= PUBLISH_PERIOD_MS) {
        last_publish_ms += PUBLISH_PERIOD_MS;
        publish();
    }
}
