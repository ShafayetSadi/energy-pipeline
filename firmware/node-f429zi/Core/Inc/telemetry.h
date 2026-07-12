#ifndef TELEMETRY_H
#define TELEMETRY_H

#include <stddef.h>
#include <stdint.h>

#include "sensor_sim.h"

/* Payloads match simulator/mqtt_publisher.py and docs/api-contract.md
 * (schema_version 1.0). Timestamp: without SNTP the node has no wall clock,
 * so it sends "1970-01-01T00:00:<uptime>" — enable LWIP_SNTP and pass real
 * epoch seconds to telemetry_set_epoch() to fix; the gateway also records
 * receive time. */

void telemetry_set_epoch(uint32_t unix_seconds); /* call from SNTP callback */

/* Build JSON telemetry into buf; returns bytes written (excl. NUL). */
size_t telemetry_json(char *buf, size_t len, const char *device_id,
                      const sensor_reading_t *r, uint32_t sequence_no);

/* Build JSON status payload ("online"/"offline"). Also used as LWT message. */
size_t status_json(char *buf, size_t len, const char *device_id,
                   const char *status);

#endif /* TELEMETRY_H */
