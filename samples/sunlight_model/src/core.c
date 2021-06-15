#include <logging/log.h>
#include <zephyr.h>
#include <zeta.h>

LOG_MODULE_DECLARE(zeta, CONFIG_ZETA_LOG_LEVEL);

K_SEM_DEFINE(CORE_callback_sem, 0, 1);


/**
 * @brief This is the function used by Zeta to tell the CORE that one(s) of the
 * channels which it is subscribed has changed. This callback will be called passing the
 * channel's id in it.
 *
 * @param id
 */
void CORE_service_callback(zt_channel_e id)
{
    k_sem_give(&CORE_callback_sem);
}

/**
 * @brief This is the task loop responsible to run the CORE thread
 * functionality.
 */
void CORE_task()
{
    LOG_DBG("CORE Service has started...[OK]");
    while (1) {
        k_sem_take(&CORE_callback_sem, K_FOREVER);
        zt_data_t* msg = ZT_DATA_SUNLIGHT_LEVEL_MSG(0);
        zt_chan_read(ZT_SUNLIGHT_LEVEL_CHANNEL, msg);
        zt_data_t* light_status = ZT_DATA_LIGHT_STATUS_MSG(0);
        light_status->light_status_msg.value.is_on =
            (msg->sunlight_level_msg.value.level <= 10);
        zt_chan_pub(ZT_LIGHT_STATUS_CHANNEL, light_status);
    }
}

ZT_SERVICE_DECLARE(CORE, CORE_task, CORE_service_callback);
