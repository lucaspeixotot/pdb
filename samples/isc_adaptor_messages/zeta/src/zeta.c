/* ***************************************************************** */
/*                      FILE GENERATED BY ZetaCLI                    */
/*                         DON'T EDIT THIS FILE                      */
/* ***************************************************************** */

#include "zeta.h"


#include <drivers/flash.h>
#include <fs/nvs.h>
#include <logging/log.h>
#include <storage/flash_map.h>
#include <string.h>
#include <zephyr.h>
#ifdef CONFIG_ZETA_FORWARDER
#include <sys/base64.h>
#endif

#include "devicetree_fixups.h"

LOG_MODULE_REGISTER(zeta, CONFIG_ZETA_LOG_LEVEL);

#define NVS_SECTOR_COUNT 4
#define NVS_STORAGE_PARTITION storage


// <ZT_CODE_INJECTION>
/* BEGIN FIRMWARE_VERSION CHANNEL INIT ARRAYS */
static uint8_t __firmware_version_data[4] = {0xf1, 0xf2, 0xf3, 0xf4};
/* END FIRMWARE_VERSION INIT ARRAYS */

/* BEGIN SENSORS CHANNEL INIT ARRAYS */
static uint8_t __sensors_data[sizeof(struct sensors_msg)] = {0};
/* END SENSORS INIT ARRAYS */

/* BEGIN NET_REQUEST CHANNEL INIT ARRAYS */
static uint8_t __net_request_data[sizeof(uint8_t)] = {0};
/* END NET_REQUEST INIT ARRAYS */

/* BEGIN NET_RESPONSE CHANNEL INIT ARRAYS */
static uint8_t __net_response_data[sizeof(uint8_t) * 5] = {0};
/* END NET_RESPONSE INIT ARRAYS */
// </ZT_CODE_INJECTION>

// <ZT_CODE_INJECTION>
zt_service_t *__zt_services[ZT_SERVICE_COUNT] = {&CORE_service, &BOARD_service, &NET_service};
// </ZT_CODE_INJECTION>

// <ZT_CODE_INJECTION>
/* BEGIN INITIALIZING CHANNEL SEMAPHORES */

K_SEM_DEFINE(zt_firmware_version_channel_sem, 1, 1);

K_SEM_DEFINE(zt_sensors_channel_sem, 1, 1);

K_SEM_DEFINE(zt_net_request_channel_sem, 1, 1);

K_SEM_DEFINE(zt_net_response_channel_sem, 1, 1);

/* END INITIALIZING CHANNEL SEMAPHORES */
// </ZT_CODE_INJECTION>

static void __zt_monitor_thread(void);
K_THREAD_DEFINE(zt_monitor_thread_id, ZT_MONITOR_THREAD_STACK_SIZE, __zt_monitor_thread,
                NULL, NULL, NULL, ZT_MONITOR_THREAD_PRIORITY, 0, 0);

#ifdef CONFIG_ZETA_STORAGE
static void __zt_storage_thread(void);
K_THREAD_DEFINE(zt_storage_thread_id, ZT_STORAGE_THREAD_STACK_SIZE, __zt_storage_thread,
                NULL, NULL, NULL, ZT_STORAGE_THREAD_PRIORITY, 0, 0);
static struct nvs_fs zt_fs;
#endif

#ifdef CONFIG_ZETA_FORWARDER
static void __zt_forwarder_thread(void);
K_THREAD_DEFINE(zt_forwarder_thread_id, ZT_FORWARDER_THREAD_STACK_SIZE,
                __zt_forwarder_thread, NULL, NULL, NULL, ZT_FORWARDER_THREAD_PRIORITY, 0,
                0);
K_MSGQ_DEFINE(zt_forwarder_msgq, sizeof(zt_isc_packet_t), 30, 4);
#endif

K_MSGQ_DEFINE(zt_channels_changed_msgq, sizeof(uint8_t), 30, 4);


// <ZT_CODE_INJECTION>
/* BEGIN INITIALIZING CHANNELS */
static zt_channel_t __zt_channels[ZT_CHANNEL_COUNT] = {

    {
        .name = "FIRMWARE_VERSION",
        .read_only = 1,
        .flag = {.data = 0},
        .size = 4,
        .persistent = 0,
        .sem = &zt_firmware_version_channel_sem,
        .id = ZT_FIRMWARE_VERSION_CHANNEL,
        .data = __firmware_version_data
    },

    {
        .name = "SENSORS",
        .read_only = 0,
        .flag = {.data = 0},
        .size = sizeof(struct sensors_msg),
        .persistent = 1,
        .sem = &zt_sensors_channel_sem,
        .id = ZT_SENSORS_CHANNEL,
        .data = __sensors_data
    },

    {
        .name = "NET_REQUEST",
        .read_only = 0,
        .flag = {.data = 0},
        .size = sizeof(uint8_t),
        .persistent = 0,
        .sem = &zt_net_request_channel_sem,
        .id = ZT_NET_REQUEST_CHANNEL,
        .data = __net_request_data
    },

    {
        .name = "NET_RESPONSE",
        .read_only = 0,
        .flag = {.data = 0},
        .size = sizeof(uint8_t) * 5,
        .persistent = 1,
        .sem = &zt_net_response_channel_sem,
        .id = ZT_NET_RESPONSE_CHANNEL,
        .data = __net_response_data
    },

};
/* END INITIALIZING CHANNELS */
// </ZT_CODE_INJECTION>

const char *zt_channel_name(zt_channel_e id, int *error)
{
    if (id < ZT_CHANNEL_COUNT) {
        zt_channel_t *p = &__zt_channels[id];
        if (error) {
            *error = 0;
        }
        return p->name;
    } else {
        LOG_INF("The channel #%d there isn't!", id);
        if (error) {
            *error = -EINVAL;
        }
        return NULL;
    }
}

size_t zt_channel_size(zt_channel_e id, int *error)
{
    if (id < ZT_CHANNEL_COUNT) {
        zt_channel_t *p = &__zt_channels[id];
        if (error) {
            *error = 0;
        }
        return (size_t) p->size;
    } else {
        LOG_INF("The channel #%d there isn't!", id);
        if (error) {
            *error = -EINVAL;
        }
        return 0;
    }
}

int zt_chan_read(zt_channel_e id, zt_data_t *channel_data)
{
    if (id < ZT_CHANNEL_COUNT) {
        zt_channel_t *channel = &__zt_channels[id];
        ZT_CHECK_VAL(channel_data, NULL, -EFAULT,
                     "publish function was called with channel_value paramater as NULL!");
        ZT_CHECK(channel_data->bytes.size != channel->size, -EINVAL,
                 "channel #%d has a different size!(%d)(%d)", id,
                 channel_data->bytes.size, channel->size);
        ZT_CHECK(k_sem_take(channel->sem, K_MSEC(200)) != 0, -EBUSY,
                 "Could not read the channel. Channel is busy");
        memcpy(channel_data->bytes.value, channel->data, channel->size);

#ifdef CONFIG_ZETA_FORWARDER
        // @TODO: When this function is called by a non Zeta service this part of code
        // will get Segmentation Fault.
        zt_service_t *current_service =
            CONTAINER_OF(k_current_get(), zt_service_t, thread);
        if (current_service != NULL) {
            zt_isc_packet_t packet = {.service_id = current_service->id,
                                      .channel_id = channel->id,
                                      .op         = ZT_FWD_OP_READ,
                                      .size       = channel->size};
            memcpy(packet.message, channel->data, packet.size);
            k_msgq_put(&zt_forwarder_msgq, &packet, K_NO_WAIT);
        }
#endif
        k_sem_give(channel->sem);
        return 0;
    } else {
        LOG_INF("The channel #%d was not found!", id);
        return -ENODATA;
    }
}

int zt_chan_pub(zt_channel_e id, zt_data_t *channel_data)
{
    if (id < ZT_CHANNEL_COUNT) {
        int error             = 0;
        zt_channel_t *channel = &__zt_channels[id];
        zt_service_t **pub;

        //@TODO: Remover este comentário. Essa modificação deve ser feita separadamente
        // for (pub = channel->publishers; *pub != NULL; ++pub) {
        //     if ((&(*pub)->thread) == k_current_get()) {
        //         break;
        //     }
        // }
        ZT_CHECK_VAL(*pub, NULL, -EACCES,
                     "The current thread has not the permission to change channel #%d!",
                     id);
        ZT_CHECK_VAL(channel_data, NULL, -EFAULT,
                     "publish function was called with channel_value paramater as NULL!");
        ZT_CHECK(channel->read_only != 0, -EPERM, "The channel #%d is read only!", id);
        ZT_CHECK(channel_data->bytes.size != channel->size, -EINVAL,
                 "The channel #%d has a different size!", id);
        ZT_CHECK(k_sem_take(channel->sem, K_MSEC(200)) != 0, -EBUSY,
                 "Could not publish the channel. Channel is busy");

#ifdef CONFIG_ZETA_FORWARDER
        zt_isc_packet_t packet = {.service_id = (*pub)->id,
                                  .channel_id = channel->id,
                                  .op         = ZT_FWD_OP_PUBLISH,
                                  .size       = channel->size};
        memcpy(packet.message, channel_data->bytes.value, packet.size);
        k_msgq_put(&zt_forwarder_msgq, &packet, K_NO_WAIT);
#endif

        if (channel->flag.field.on_changed) {  // CHANGE
            if (memcmp(channel->data, channel_data->bytes.value, channel->size) == 0) {
                channel->flag.field.pend_callback = 0;
                k_sem_give(channel->sem);
                return 0;
            }
        }
        channel->flag.field.pend_callback = 1;
        memcpy(channel->data, channel_data->bytes.value, channel->size);
        error = k_msgq_put(&zt_channels_changed_msgq, (uint8_t *) &id, K_MSEC(500));
        if (error != 0) {
            LOG_INF("[Channel #%d] Error sending channels change message to ZT "
                    "thread!",
                    id);
        }
        channel->flag.field.pend_persistent = (channel->persistent) ? 1 : 0;
        k_sem_give(channel->sem);
        return error;
    } else {
        LOG_INF("The channel #%d was not found!", id);
        return -ENODATA;
    }
}

static void __zt_monitor_thread(void)
{
    // <ZT_CODE_INJECTION>
/* BEGIN FIRMWARE_VERSION PUBLISHERS INIT */
    zt_service_t *firmware_version_publishers[] = {NULL};
    __zt_channels[ZT_FIRMWARE_VERSION_CHANNEL].publishers = firmware_version_publishers;
/* END FIRMWARE_VERSION PUBLISHERS INIT */

/* BEGIN SENSORS PUBLISHERS INIT */
    zt_service_t *sensors_publishers[] = {&BOARD_service, NULL};
    __zt_channels[ZT_SENSORS_CHANNEL].publishers = sensors_publishers;
/* END SENSORS PUBLISHERS INIT */

/* BEGIN NET_REQUEST PUBLISHERS INIT */
    zt_service_t *net_request_publishers[] = {&NET_service, NULL};
    __zt_channels[ZT_NET_REQUEST_CHANNEL].publishers = net_request_publishers;
/* END NET_REQUEST PUBLISHERS INIT */

/* BEGIN NET_RESPONSE PUBLISHERS INIT */
    zt_service_t *net_response_publishers[] = {&CORE_service, NULL};
    __zt_channels[ZT_NET_RESPONSE_CHANNEL].publishers = net_response_publishers;
/* END NET_RESPONSE PUBLISHERS INIT */
    // </ZT_CODE_INJECTION>

    // <ZT_CODE_INJECTION>
/* BEGIN FIRMWARE_VERSION SUBSCRIBERS INIT */
    zt_service_t *firmware_version_subscribers[] = {NULL};
    __zt_channels[ZT_FIRMWARE_VERSION_CHANNEL].subscribers = firmware_version_subscribers;
/* END FIRMWARE_VERSION SUBSCRIBERS INIT */

/* BEGIN SENSORS SUBSCRIBERS INIT */
    zt_service_t *sensors_subscribers[] = {&CORE_service, NULL};
    __zt_channels[ZT_SENSORS_CHANNEL].subscribers = sensors_subscribers;
/* END SENSORS SUBSCRIBERS INIT */

/* BEGIN NET_REQUEST SUBSCRIBERS INIT */
    zt_service_t *net_request_subscribers[] = {&CORE_service, NULL};
    __zt_channels[ZT_NET_REQUEST_CHANNEL].subscribers = net_request_subscribers;
/* END NET_REQUEST SUBSCRIBERS INIT */

/* BEGIN NET_RESPONSE SUBSCRIBERS INIT */
    zt_service_t *net_response_subscribers[] = {&NET_service, NULL};
    __zt_channels[ZT_NET_RESPONSE_CHANNEL].subscribers = net_response_subscribers;
/* END NET_RESPONSE SUBSCRIBERS INIT */
    // </ZT_CODE_INJECTION>

    // <ZT_CODE_INJECTION>
    ZT_SERVICE_RUN(CORE);
    ZT_SERVICE_RUN(BOARD);
    ZT_SERVICE_RUN(NET);
    // </ZT_CODE_INJECTION>

    uint8_t id = 0;
    while (1) {
        k_msgq_get(&zt_channels_changed_msgq, &id, K_FOREVER);
        if (id < ZT_CHANNEL_COUNT) {
            if (__zt_channels[id].flag.field.pend_callback) {
                for (zt_service_t **s = __zt_channels[id].subscribers; *s != NULL; ++s) {
                    (*s)->cb(id);
#ifdef CONFIG_ZETA_FORWARDER
                    zt_isc_packet_t packet = {
                        .service_id = (*s)->id,
                        .channel_id = id,
                        .op         = ZT_FWD_OP_CALLBACK,
                    };
                    k_msgq_put(&zt_forwarder_msgq, &packet, K_NO_WAIT);
#endif
                }
                __zt_channels[id].flag.field.pend_callback = 0;
            } else {
                LOG_INF("[ZT-THREAD]: Received pend_callback from a channel(#%d) "
                        "without changes!",
                        id);
            }
        } else {
            LOG_INF("[ZT-THREAD]: Received an invalid ID channel #%d", id);
        }
    }
}

#ifdef CONFIG_ZETA_STORAGE

static void __zt_recover_data_from_flash(void)
{
    int rc = 0;
    LOG_INF("[ ] Recovering data from flash");
    for (uint16_t id = 0; id < ZT_CHANNEL_COUNT; ++id) {
        if (__zt_channels[id].persistent) {
            if (!k_sem_take(__zt_channels[id].sem, K_SECONDS(5))) {
                rc = nvs_read(&zt_fs, id, __zt_channels[id].data, __zt_channels[id].size);
                if (rc > 0) { /* item was found, show it */
                    LOG_INF("Id: %d", id);
                    LOG_HEXDUMP_INF(__zt_channels[id].data, __zt_channels[id].size,
                                    "Value: ");
                } else { /* item was not found, add it */
                    LOG_INF("No values found for channel #%d", id);
                }
                k_sem_give(__zt_channels[id].sem);
            } else {
                LOG_INF("Could not recover the channel. Channel is busy");
            }
        }
    }
    LOG_INF("[X] Recovering data from flash");
}

static void __zt_persist_data_on_flash(void)
{
    int bytes_written = 0;
    for (uint16_t id = 0; id < ZT_CHANNEL_COUNT; ++id) {
        if (__zt_channels[id].persistent
            && __zt_channels[id].flag.field.pend_persistent) {
            bytes_written =
                nvs_write(&zt_fs, id, __zt_channels[id].data, __zt_channels[id].size);
            if (bytes_written > 0) { /* item was found and updated*/
                __zt_channels[id].flag.field.pend_persistent = 0;
#ifdef CONFIG_ZETA_FORWARDER
                zt_isc_packet_t packet = {
                    .service_id = ZT_SERVICE_COUNT,
                    .channel_id = id,
                    .op         = ZT_FWD_OP_SAVED,
                };
                k_msgq_put(&zt_forwarder_msgq, &packet, K_NO_WAIT);
#endif
                LOG_INF("channel #%d value updated on the flash", id);
            } else if (bytes_written == 0) {
                /* LOG_INF("channel #%d value is already on the flash.", id); */
            } else { /* item was not found, add it */
                LOG_INF("channel #%d could not be stored", id);
            }
        }
    }
}

static void __zt_storage_thread(void)
{
    struct flash_pages_info info;
    zt_fs.offset = FLASH_AREA_OFFSET(NVS_STORAGE_PARTITION);
    int rc       = flash_get_page_info_by_offs(
        device_get_binding(DT_CHOSEN_ZEPHYR_FLASH_CONTROLLER_LABEL), zt_fs.offset, &info);
    if (rc) {
        printk("Unable to get page info");
    }
    zt_fs.sector_size  = info.size;
    zt_fs.sector_count = NVS_SECTOR_COUNT;
    rc                 = nvs_init(&zt_fs, DT_CHOSEN_ZEPHYR_FLASH_CONTROLLER_LABEL);
    if (rc) {
        LOG_INF("Flash Init failed");
    } else {
        LOG_INF("NVS started...[OK]");
    }
    __zt_recover_data_from_flash();

    while (1) {
        k_sleep(K_SECONDS(ZT_STORAGE_SLEEP_TIME));
        __zt_persist_data_on_flash();
    }
}

#endif

#ifdef CONFIG_ZETA_FORWARDER
static void __zt_forwarder_thread(void)
{
    zt_isc_packet_t packet  = {0};
    uint32_t packet_counter = 0;
    uint8_t *data;

    uint8_t buffer[272] = {0};
    size_t len;

    while (1) {
        k_msgq_get(&zt_forwarder_msgq, &packet, K_FOREVER);
        data      = (uint8_t *) &packet;
        packet.id = packet_counter++;

        base64_encode(buffer, sizeof(buffer), &len, data, 8 + packet.size);

        printk("@ZT_ISC:%s\n", buffer);
        memset(buffer, 0, 272);
    }
}
#endif
