#include "mqtt_app.h"

#include <stdio.h>
#include <string.h>

#include "lwip/apps/mqtt.h"
#include "lwip/ip_addr.h"
#include "stm32f4xx_hal.h"

#include "sensor_sim.h"
#include "telemetry.h"

#define TOPIC_TELEMETRY MQTT_BASE_TOPIC "/" MQTT_DEVICE_ID "/telemetry"
#define TOPIC_STATUS    MQTT_BASE_TOPIC "/" MQTT_DEVICE_ID "/status"

static mqtt_client_t *client;
static ip_addr_t broker_ip;
static volatile int connected;
static uint32_t next_publish_ms;
static uint32_t next_status_ms;
static uint32_t next_reconnect_ms;
static uint32_t sequence_no;
static char lwt_buf[160];
static char msg_buf[288];

static void connection_cb(mqtt_client_t *c, void *arg,
                          mqtt_connection_status_t status)
{
    (void)c; (void)arg;
    connected = (status == MQTT_CONNECT_ACCEPTED);
    printf("[mqtt] connection status: %d\r\n", (int)status);
}

static void do_connect(void)
{
    struct mqtt_connect_client_info_t ci;
    memset(&ci, 0, sizeof ci);
    ci.client_id = MQTT_DEVICE_ID;
    ci.keep_alive = 30;
    /* LWT: broker publishes "offline" status if the node dies. */
    status_json(lwt_buf, sizeof lwt_buf, MQTT_DEVICE_ID, "offline");
    ci.will_topic = TOPIC_STATUS;
    ci.will_msg = lwt_buf;
    ci.will_qos = 1;
    ci.will_retain = 0;

    printf("[mqtt] connecting to %s:%d\r\n", MQTT_BROKER_IP, MQTT_BROKER_PORT);
    mqtt_client_connect(client, &broker_ip, MQTT_BROKER_PORT,
                        connection_cb, NULL, &ci);
}

void mqtt_app_init(void)
{
    ipaddr_aton(MQTT_BROKER_IP, &broker_ip);
    client = mqtt_client_new();
    do_connect();
}

static void publish(const char *topic, const char *payload, u8_t qos)
{
    err_t err = mqtt_publish(client, topic, payload, (u16_t)strlen(payload),
                             qos, 0, NULL, NULL);
    if (err != ERR_OK)
        printf("[mqtt] publish err %d on %s\r\n", (int)err, topic);
}

void mqtt_app_poll(void)
{
    uint32_t now = HAL_GetTick();

    if (!connected) {
        if (now >= next_reconnect_ms) {
            next_reconnect_ms = now + 5000u;
            if (!mqtt_client_is_connected(client))
                do_connect();
        }
        return;
    }

    if (now >= next_status_ms) {
        next_status_ms = now + STATUS_INTERVAL_MS;
        status_json(msg_buf, sizeof msg_buf, MQTT_DEVICE_ID, "online");
        publish(TOPIC_STATUS, msg_buf, 1);
    }

    if (now >= next_publish_ms) {
        next_publish_ms = now + PUBLISH_INTERVAL_MS;
        sensor_reading_t r;
        /* 200 samples over 40 ms = two 50 Hz cycles. */
        sensor_measure(&r, 200, 40);
        telemetry_json(msg_buf, sizeof msg_buf, MQTT_DEVICE_ID, &r,
                       ++sequence_no);
        publish(TOPIC_TELEMETRY, msg_buf, 0);
        printf("[node] seq=%lu V=%.1f I=%.2f P=%.0f\r\n",
               (unsigned long)sequence_no, (double)r.voltage_v,
               (double)r.current_a, (double)r.power_w);
    }
}
