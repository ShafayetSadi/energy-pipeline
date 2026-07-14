#ifndef TELEMETRY_H
#define TELEMETRY_H

#include <stddef.h>
#include <stdint.h>

#include "measurement.h"

/* Payloads match the pipeline API contract (schema_version 1.0) so the gateway
 * treats this node like any other device.
 *
 * Wall clock: the Black Pill has no network time. If a battery-backed RTC is
 * set, timestamps are real; otherwise call telemetry_set_epoch() once with a
 * seed (e.g. build time or a value pushed from the ESP-01). The gateway also
 * records receive time, so an unsynced node still ingests. */

void telemetry_set_epoch(uint32_t unix_seconds);

/* Build JSON telemetry into buf; returns bytes written (excl. NUL). */
size_t telemetry_json(char *buf, size_t len, const char *device_id,
                      const sensor_reading_t *r, uint32_t sequence_no);

/* Build JSON status payload ("online"/"offline"). Also used as LWT message. */
size_t status_json(char *buf, size_t len, const char *device_id,
                   const char *status);

#endif /* TELEMETRY_H */
