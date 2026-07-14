#include "esp01_mqtt.h"

#include <string.h>

#include "stm32f4xx_hal.h"

static UART_HandleTypeDef *uart;

#define TX_TIMEOUT_MS 200u

void esp01_init(void *huart)
{
    uart = (UART_HandleTypeDef *)huart;
}

static bool tx(const char *s, size_t len)
{
    return HAL_UART_Transmit(uart, (uint8_t *)s, (uint16_t)len,
                             TX_TIMEOUT_MS) == HAL_OK;
}

bool esp01_publish(const char *topic, const char *payload)
{
    if (uart == NULL)
        return false;
    return tx(topic, strlen(topic))
        && tx(" ", 1)
        && tx(payload, strlen(payload))
        && tx("\n", 1);
}
