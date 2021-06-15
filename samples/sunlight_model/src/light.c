#include <device.h>
#include <devicetree.h>
#include <drivers/gpio.h>
#include <logging/log.h>
#include <zephyr.h>
#include <zeta.h>

LOG_MODULE_DECLARE(zeta, CONFIG_ZETA_LOG_LEVEL);

/* The devicetree node identifier for the "led0" alias. */
#define LED0_NODE DT_ALIAS(led0)

#if DT_NODE_HAS_STATUS(LED0_NODE, okay)
#define LED0 DT_GPIO_LABEL(LED0_NODE, gpios)
#define PIN DT_GPIO_PIN(LED0_NODE, gpios)
#define FLAGS DT_GPIO_FLAGS(LED0_NODE, gpios)
#else
/* A build error here means your board isn't set up to blink an LED. */
#error "Unsupported board: led0 devicetree alias is not defined"
#define LED0 ""
#define PIN 0
#define FLAGS 0
#endif

K_SEM_DEFINE(LIGHT_callback_sem, 0, 1);


/**
 * @brief This is the function used by Zeta to tell the LIGHT that one(s) of the
 * channels which it is subscribed has changed. This callback will be called passing the
 * channel's id in it.
 *
 * @param id
 */
void LIGHT_service_callback(zt_channel_e id)
{
    k_sem_give(&LIGHT_callback_sem);
}

/**
 * @brief This is the task loop responsible to run the LIGHT thread
 * functionality.
 */
void LIGHT_task()
{
    LOG_DBG("LIGHT Service has started...[OK]");
    const struct device* dev;
    int ret;

    dev = device_get_binding(LED0);
    if (dev == NULL) {
        return;
    }

    ret = gpio_pin_configure(dev, PIN, GPIO_OUTPUT_ACTIVE | FLAGS);
    if (ret < 0) {
        return;
    }

    while (1) {
        k_sem_take(&LIGHT_callback_sem, K_FOREVER);
        zt_data_t* msg = ZT_DATA_LIGHT_STATUS_MSG(0);
        zt_chan_read(ZT_LIGHT_STATUS_CHANNEL, msg);
        gpio_pin_set(dev, PIN, (int) msg->light_status_msg.value.is_on);
    }
}

ZT_SERVICE_DECLARE(LIGHT, LIGHT_task, LIGHT_service_callback);
