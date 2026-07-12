#ifndef MQTT_APP_H
#define MQTT_APP_H

/* MQTT application layer on LwIP's built-in client (lwip/apps/mqtt.h).
 * Call mqtt_app_init() once after MX_LWIP_Init(), then mqtt_app_poll()
 * from the main loop alongside MX_LWIP_Process(). */

#ifndef MQTT_BROKER_IP
#define MQTT_BROKER_IP        "192.168.100.1"  /* host end of Renode TAP */
#endif
#ifndef MQTT_BROKER_PORT
#define MQTT_BROKER_PORT      18831            /* docker-compose host port */
#endif
#ifndef MQTT_DEVICE_ID
#define MQTT_DEVICE_ID        "stm32_0001"
#endif
#ifndef MQTT_BASE_TOPIC
#define MQTT_BASE_TOPIC       "energy"
#endif
#ifndef PUBLISH_INTERVAL_MS
#define PUBLISH_INTERVAL_MS   1000u
#endif
#ifndef STATUS_INTERVAL_MS
#define STATUS_INTERVAL_MS    15000u
#endif

void mqtt_app_init(void);
void mqtt_app_poll(void);

#endif /* MQTT_APP_H */
