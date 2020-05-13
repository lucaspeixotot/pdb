/* ***************************************************************** */
/*                      FILE GENERATED BY ZetaCLI                    */
/*                         DON'T EDIT THIS FILE                      */
/* ***************************************************************** */

/**
 * @file   zeta.template.c
 * @author Rodrigo Peixoto
 * @author Lucas Peixoto <lucaspeixotoac@gmail.com>
 *
 *
 *
 */
#include "zeta.h"


#include <fs/nvs.h>
#include <logging/log.h>
#include <string.h>
#include <zephyr.h>

#include "devicetree_fixups.h"
#include "zeta_custom_functions.h"


LOG_MODULE_REGISTER(zeta, CONFIG_ZETA_LOG_LEVEL);

// <ZT_CODE_INJECTION>$arrays_init// </ZT_CODE_INJECTION>

#define NVS_SECTOR_SIZE $nvs_sector_size
#define NVS_SECTOR_COUNT $nvs_sector_count
#define NVS_STORAGE_OFFSET $nvs_storage_offset

// <ZT_CODE_INJECTION>$channels_sems// </ZT_CODE_INJECTION>

static void __zt_channels_thread(void);
static void __zt_storage_thread(void);
static int __zt_channel_read_private(zt_channel_e id, u8_t *channel_value, size_t size);
static int __zt_channel_publish_private(zt_channel_e id, u8_t *channel_value,
                                        size_t size);

K_THREAD_DEFINE(zt_channels_thread_id, ZT_CHANNELS_THREAD_STACK_SIZE,
                __zt_channels_thread, NULL, NULL, NULL, ZT_THREADS_PRIORITY, 0,
                K_NO_WAIT);

K_THREAD_DEFINE(zt_storage_thread_id, ZT_STORAGE_THREAD_STACK_SIZE, __zt_storage_thread,
                NULL, NULL, NULL, ZT_THREADS_PRIORITY, 0, K_NO_WAIT);
K_MSGQ_DEFINE(zt_channels_changed_msgq, sizeof(u8_t), 30, 4);


static struct nvs_fs zt_fs = {
    .sector_size  = NVS_SECTOR_SIZE,
    .sector_count = NVS_SECTOR_COUNT,
    .offset       = NVS_STORAGE_OFFSET,
};

// <ZT_CODE_INJECTION>$channels_creation// </ZT_CODE_INJECTION>

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

int zt_channel_data_read(zt_channel_e id, zt_data_t *channel_data)
{
    return zt_channel_read(id, channel_data->bytes.value, channel_data->bytes.size);
}

int zt_channel_read(zt_channel_e id, u8_t *channel_value, size_t size)
{
    if (id < ZT_CHANNEL_COUNT) {
        int error             = 0;
        zt_channel_t *channel = &__zt_channels[id];
        ZT_CHECK_VAL(channel_value, NULL, -EFAULT,
                     "read function was called with channel_value parameter as NULL!");
        ZT_CHECK_VAL(channel->read, NULL, -EPERM,
                     "channel #%d does not have read implementation!", id);
        ZT_CHECK(size != channel->size, -EINVAL,
                 "channel #%d has a different size!(%d)(%d)", id, size, channel->size);
        if (channel->pre_read) {
            error = channel->pre_read(id, channel_value, size);
            ZT_CHECK(error, error, "Error(code %d) in pre-read function of channel #%d",
                     error, id);
        }
        error = channel->read(id, channel_value, size);
        ZT_CHECK(error, error, "Current channel #%d, error code: %d", id, error);
        if (channel->pos_read) {
            error = channel->pos_read(id, channel_value, size);
            ZT_CHECK(error, error, "Error(code %d) in pos-read function of channel #%d!",
                     error, id);
        }
        return error;
    } else {
        LOG_INF("The channel #%d was not found!", id);
        return -ENODATA;
    }
}

static int __zt_channel_read_private(zt_channel_e id, u8_t *channel_value, size_t size)
{
    int ret               = 0;
    zt_channel_t *channel = &__zt_channels[id];
    if (k_sem_take(channel->sem, K_MSEC(200))) {
        LOG_INF("Could not read the channel. Channel is busy");
        ret = -EBUSY;
    } else {
        memcpy(channel_value, channel->data, channel->size);
        k_sem_give(channel->sem);
    }
    return ret;
}

int zt_channel_data_publish(zt_channel_e id, zt_data_t *channel_data)
{
    return zt_channel_publish(id, channel_data->bytes.value, channel_data->bytes.size);
}

int zt_channel_publish(zt_channel_e id, u8_t *channel_value, size_t size)
{
    if (id < ZT_CHANNEL_COUNT) {
        int error             = 0;
        int valid             = 1;
        zt_channel_t *channel = &__zt_channels[id];
        zt_service_t **pub;

        for (pub = channel->publishers; *pub != NULL; ++pub) {
            if ((*(*pub)->thread_id) == k_current_get()) {
                break;
            }
        }
        ZT_CHECK_VAL(*pub, NULL, -EACCES,
                     "The current thread has not the permission to change channel #%d!",
                     id);
        ZT_CHECK_VAL(channel_value, NULL, -EFAULT,
                     "publish function was called with channel_value paramater as NULL!");
        ZT_CHECK_VAL(channel->publish, NULL, -EPERM, "The channel #%d is read only!", id);
        ZT_CHECK(size != channel->size, -EINVAL, "The channel #%d has a different size!",
                 id);
        if (channel->validate) {
            valid = channel->validate(channel_value, size);
        }
        ZT_CHECK(!valid, -EAGAIN,
                 "The value doesn't satisfy valid function of channel #%d!", id);
        if (channel->pre_publish) {
            error = channel->pre_publish(id, channel_value, size);
            ZT_CHECK(error, error, "Error on pre_publish function of channel #%d!", id);
        }
        error = channel->publish(id, channel_value, size);
        ZT_CHECK(error, error, "Current channel #%d, error code: %d!", id, error);
        if (channel->pos_publish) {
            error = channel->pos_publish(id, channel_value, size);
            ZT_CHECK(error, error, "Error on pos_publish function of channel #%d!", id);
        }
        return error;
    } else {
        LOG_INF("The channel #%d was not found!", id);
        return -ENODATA;
    }
}

static int __zt_channel_publish_private(zt_channel_e id, u8_t *channel_value, size_t size)
{
    int ret               = 0;
    zt_channel_t *channel = &__zt_channels[id];
    if (k_sem_take(channel->sem, K_MSEC(200))) {
        LOG_INF("Could not publish the channel. Channel is busy");
        ret = -EBUSY;
    } else {
        if (memcmp(channel->data, channel_value, channel->size)) {
            memcpy(channel->data, channel_value, channel->size);
        }
        channel->opt.field.pend_callback = 1;
        if (k_msgq_put(&zt_channels_changed_msgq, (u8_t *) &id, K_MSEC(500))) {
            LOG_INF("[Channel #%d] Error sending channels change message to ZT thread!",
                    id);
        }
        channel->opt.field.pend_persistent = (channel->persistent) ? 1 : 0;
        k_sem_give(channel->sem);
    }
    return ret;
}

static void __zt_recover_data_from_flash(void)
{
    int rc = 0;
    LOG_INF("[ ] Recovering data from flash");
    for (u16_t id = 0; id < ZT_CHANNEL_COUNT; ++id) {
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
    for (u16_t id = 0; id < ZT_CHANNEL_COUNT; ++id) {
        if (__zt_channels[id].persistent && __zt_channels[id].opt.field.pend_persistent) {
            // LOG_INF("Store changes for channel #%d", id);
            bytes_written =
                nvs_write(&zt_fs, id, __zt_channels[id].data, __zt_channels[id].size);
            if (bytes_written > 0) { /* item was found and updated*/
                __zt_channels[id].opt.field.pend_persistent = 0;
                LOG_INF("channel #%d value updated on the flash", id);
            } else if (bytes_written == 0) {
                /* LOG_INF("channel #%d value is already on the flash.", id); */
            } else { /* item was not found, add it */
                LOG_INF("channel #%d could not be stored", id);
            }
        }
    }
}

void __zt_channels_thread(void)
{
    // <ZT_CODE_INJECTION>$set_publishers    // </ZT_CODE_INJECTION>

    // <ZT_CODE_INJECTION>$set_subscribers    // </ZT_CODE_INJECTION>

    u8_t id = 0;
    while (1) {
        k_msgq_get(&zt_channels_changed_msgq, &id, K_FOREVER);
        if (id < ZT_CHANNEL_COUNT) {
            if (__zt_channels[id].opt.field.pend_callback) {
                for (zt_service_t **s = __zt_channels[id].subscribers; *s != NULL; ++s) {
                    (*s)->cb(id);
                }
                __zt_channels[id].opt.field.pend_callback = 0;
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

void __zt_storage_thread(void)
{
    int error = nvs_init(&zt_fs, DT_FLASH_DEV_NAME);
    if (error) {
        LOG_INF("Flash Init failed");
    } else {
        LOG_INF("NVS started...[OK]");
    }
    __zt_recover_data_from_flash();

    while (1) {
        k_sleep(K_SECONDS(10));
        __zt_persist_data_on_flash();
    }
}
