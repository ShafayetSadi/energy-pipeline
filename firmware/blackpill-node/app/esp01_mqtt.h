#ifndef ESP01_MQTT_H
#define ESP01_MQTT_H

#include <stdbool.h>
#include <stddef.h>

/* Uplink to the ESP-01 (ESP8266) over UART. The STM32 stays trivial: it emits
 * one newline-terminated line per message. The ESP-01 sketch (see esp01/) owns
 * Wi-Fi + MQTT and publishes each line. Line protocol:
 *
 *     <topic> <json>\n
 *
 * e.g.  energy/stm32_0001/telemetry {"schema_version":"1.0",...}\n
 */

/* Pass the CubeMX UART handle (void* keeps this header HAL-free). */
void esp01_init(void *huart);

/* Send "<topic> <payload>\n". Returns false on UART error/timeout. */
bool esp01_publish(const char *topic, const char *payload);

#endif /* ESP01_MQTT_H */
