#include "telemetry.h"

#include <stdio.h>

#include "stm32f4xx_hal.h"

#include "../config.h"

static uint32_t epoch_base = 0;      /* unix seconds at tick_base, 0 = unset */
static uint32_t tick_base_ms = 0;

void telemetry_set_epoch(uint32_t unix_seconds)
{
    epoch_base = unix_seconds;
    tick_base_ms = HAL_GetTick();
}

/* Days since 1970-01-01 for a civil date (Howard Hinnant's algorithm). */
static uint32_t days_from_civil(int y, int m, int d)
{
    y -= m <= 2;
    int era = y / 400;
    int yoe = y - era * 400;
    int doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    int doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return (uint32_t)(era * 146097 + doe - 719468);
}

/* Read the calendar from the RTC (BCD registers). Returns 0 if the RTC has
 * never been set (reset date 2000-01-01), e.g. a fresh board with no backup
 * battery. Same register layout across the STM32F4 family. */
static uint32_t rtc_read_epoch(void)
{
    volatile uint32_t *rtc_tr = (uint32_t *)0x40002800u;
    volatile uint32_t *rtc_dr = (uint32_t *)0x40002804u;
    uint32_t tr = *rtc_tr, dr = *rtc_dr;

    int yy = (int)(((dr >> 20) & 0xF) * 10 + ((dr >> 16) & 0xF));
    int mo = (int)(((dr >> 12) & 0x1) * 10 + ((dr >> 8) & 0xF));
    int dd = (int)(((dr >> 4) & 0x3) * 10 + (dr & 0xF));
    int hh = (int)(((tr >> 20) & 0x3) * 10 + ((tr >> 16) & 0xF));
    int mi = (int)(((tr >> 12) & 0x7) * 10 + ((tr >> 8) & 0xF));
    int ss = (int)(((tr >> 4) & 0x7) * 10 + (tr & 0xF));

    if (yy == 0 || mo == 0 || dd == 0) /* RTC never set */
        return 0;
    return days_from_civil(2000 + yy, mo, dd) * 86400u
         + (uint32_t)hh * 3600u + (uint32_t)mi * 60u + (uint32_t)ss;
}

/* ISO-8601 UTC from epoch seconds (civil-from-days algorithm). */
static void iso8601_now(char *buf, size_t len)
{
    if (epoch_base == 0)
        telemetry_set_epoch(rtc_read_epoch());

    uint32_t secs = epoch_base + (HAL_GetTick() - tick_base_ms) / 1000u;
    uint32_t days = secs / 86400u, rem = secs % 86400u;
    uint32_t hh = rem / 3600u, mm = (rem % 3600u) / 60u, ss = rem % 60u;

    int64_t z = (int64_t)days + 719468;
    int64_t era = z / 146097;
    int64_t doe = z - era * 146097;
    int64_t yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    int64_t y = yoe + era * 400;
    int64_t doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    int64_t mp = (5 * doy + 2) / 153;
    int64_t d = doy - (153 * mp + 2) / 5 + 1;
    int64_t m = mp < 10 ? mp + 3 : mp - 9;
    if (m <= 2) y++;

    snprintf(buf, len, "%04ld-%02ld-%02ldT%02lu:%02lu:%02lu+00:00",
             (long)y, (long)m, (long)d,
             (unsigned long)hh, (unsigned long)mm, (unsigned long)ss);
}

size_t telemetry_json(char *buf, size_t len, const char *device_id,
                      const sensor_reading_t *r, uint32_t sequence_no)
{
    char ts[40];
    iso8601_now(ts, sizeof ts);
    int n = snprintf(buf, len,
        "{\"schema_version\":\"1.0\",\"device_id\":\"%s\","
        "\"timestamp\":\"%s\","
        "\"voltage_v\":%.2f,\"current_a\":%.3f,\"power_w\":%.2f,"
        "\"temperature_c\":%.1f,\"sequence_no\":%lu}",
        device_id, ts,
        (double)r->voltage_v, (double)r->current_a, (double)r->power_w,
        (double)r->temperature_c, (unsigned long)sequence_no);
    return n > 0 ? (size_t)n : 0;
}

size_t status_json(char *buf, size_t len, const char *device_id,
                   const char *status)
{
    char ts[40];
    iso8601_now(ts, sizeof ts);
    int n = snprintf(buf, len,
        "{\"schema_version\":\"1.0\",\"device_id\":\"%s\","
        "\"status\":\"%s\",\"timestamp\":\"%s\","
        "\"firmware_version\":\"" NODE_FIRMWARE_VERSION "\",\"rssi_dbm\":-50}",
        device_id, status, ts);
    return n > 0 ? (size_t)n : 0;
}
