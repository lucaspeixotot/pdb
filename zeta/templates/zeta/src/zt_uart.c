#include "zt_uart.h"
#include <drivers/uart.h>
#include <zephyr.h>

static const struct device *__uart_dev = 0;
K_MSGQ_DEFINE(__input_msgq, sizeof(uint8_t), 512, 1);
K_MSGQ_DEFINE(__output_msgq, sizeof(uint8_t), 512, 1);

const struct uart_config uart_cfg = {.baudrate  = 115200,
                                     .parity    = UART_CFG_PARITY_NONE,
                                     .stop_bits = UART_CFG_STOP_BITS_1,
                                     .data_bits = UART_CFG_DATA_BITS_8,
                                     .flow_ctrl = UART_CFG_FLOW_CTRL_NONE};

static void uart_fifo_callback(const struct device *dev, void *user_data)
{
    uint8_t data = 0;
    if (!uart_irq_update(dev)) {
        return;
    }

    if (uart_irq_tx_ready(dev)) {
        if (!k_msgq_get(&__output_msgq, &data, K_NO_WAIT)) {
            uart_fifo_fill(dev, &data, sizeof(uint8_t));
        } else {
            uart_irq_tx_disable(dev);
        }
    }

    data = 0;

    if (uart_irq_rx_ready(dev)) {
        uart_fifo_read(dev, &data, sizeof(uint8_t));
        k_msgq_put(&__input_msgq, &data, K_NO_WAIT);
    }
}

struct k_msgq *uart_get_input_msgq()
{
    return &__input_msgq;
}

struct k_msgq *uart_get_output_msgq()
{
    return &__output_msgq;
}

int uart_open(char *dev_label)
{
    const struct device *dev = device_get_binding(dev_label);
    __uart_dev               = dev;

    if (dev == NULL) {
        printk("The UART device was not found.\n");
        return -EINVAL;
    }
#if 0  //! defined(CONFIG_BOARD_NATIVE_POSIX_32BIT)

    /* Verify configure() - set device configuration using data in cfg */
    int ret = uart_configure(dev, &uart_cfg);

    if (ret == -ENOTSUP) {
        return -ENOTSUP;
    }
#endif
    uart_irq_callback_set(dev, uart_fifo_callback);
    uart_irq_rx_enable(dev);

    return 0;
}

int uart_write(uint8_t *data, size_t size)
{
    if (__uart_dev == NULL) {
        return -ENODEV;
    }
    int err            = 0;
    uint8_t *data_end  = data + size;
    uint8_t *data_iter = data;
    for (; data_iter < data_end; ++data_iter) {
        err = err || k_msgq_put(&__output_msgq, data_iter, K_MSEC(10));
    }

    uart_irq_tx_enable(__uart_dev);

    return err;
}

int uart_write_str(char *str)
{
    if (__uart_dev == NULL) {
        return -ENODEV;
    }
    int err         = 0;
    char *data_iter = str;
    for (; *data_iter != '\0'; ++data_iter) {
        err = err || k_msgq_put(&__output_msgq, data_iter, K_MSEC(10));
    }

    uart_irq_tx_enable(__uart_dev);

    return err;
}

int uart_write_byte(uint8_t *byte)
{
    if (__uart_dev == NULL) {
        return -ENODEV;
    }
    int err = k_msgq_put(&__output_msgq, byte, K_MSEC(10));
    if (!err) {
        uart_irq_tx_enable(__uart_dev);
    }
    return err;
}
