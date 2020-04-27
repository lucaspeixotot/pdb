/*
 * Copyright (c) 2012-2014 Wind River Systems, Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <zephyr.h>

#include "autoconf.h"
#include "zeta.h"
#include "zeta_threads.h"

K_SEM_DEFINE(zeta_core_pend_evt, 0, 1);
K_SEM_DEFINE(zeta_app_pend_evt, 0, 1);

zeta_channel_e zeta_core_evt_id;
zeta_channel_e zeta_app_evt_id;

int zeta_validator_different_of_zero(u8_t *data, size_t size)
{
    return 1;
}

void HAL_task(void)
{
    u8_t data = 1;
    while (1) {
        zeta_channel_set(ZETA_SENSOR_VAL_CHANNEL, (u8_t *) &data, sizeof(data));
        k_sleep(K_SECONDS(3));
        data = (data + 1 <= 15) ? data + 1 : 1;
    }
}

void CORE_task(void)
{
    u8_t data  = 0;
    u8_t power = 2;

    while (1) {
        u16_t result = 1;
        k_sem_take(&zeta_core_pend_evt, K_FOREVER);
        switch (zeta_core_evt_id) {
        case ZETA_SENSOR_VAL_CHANNEL:
            zeta_channel_get(zeta_core_evt_id, (u8_t *) &data, sizeof(data));
            printk("[CORE_service_callback] Getting data value %02X\n", data);
            for (u8_t i = 1; i <= data; ++i) {
                result = result * power;
            }
            zeta_channel_set(ZETA_POWER_VAL_CHANNEL, (u8_t *) &result, sizeof(result));
            break;
        default:
            printk("[CORE_service_callback] receiving an unexpected id channel\n");
            break;
        }
    }
}

void APP_task(void)
{
    u8_t fv[4] = {0};
    printk("Hello APP task!\n");
    zeta_channel_get(ZETA_FIRMWARE_VERSION_CHANNEL, fv, sizeof(fv));
    printk("Firmware version 0x%02X%02X%02X%02X\n", fv[0], fv[1], fv[2], fv[3]);
    u16_t data = 0;
    while (1) {
        k_sem_take(&zeta_app_pend_evt, K_FOREVER);
        switch (zeta_app_evt_id) {
        case ZETA_POWER_VAL_CHANNEL:
            zeta_channel_get(zeta_app_evt_id, (u8_t *) &data, sizeof(data));
            printk("[APP_service_callback] Power val is: %04X\n", data);
            break;
        default:
            printk("[APP_service_callback] receiving an unexpected id channel\n");
        }
    }
}

void CORE_service_callback(zeta_channel_e id)
{
    zeta_core_evt_id = id;
    k_sem_give(&zeta_core_pend_evt);
}

void HAL_service_callback(zeta_channel_e id)
{
}

void APP_service_callback(zeta_channel_e id)
{
    zeta_app_evt_id = id;
    k_sem_give(&zeta_app_pend_evt);
}

void main(void)
{
    printk("******** ZETA test! *******\n");
}
