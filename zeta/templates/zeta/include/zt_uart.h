#ifndef _ZT_UART_H_
#define _ZT_UART_H_

#include <device.h>
#include <zephyr.h>

int uart_open(char *dev_label);

int uart_write(uint8_t *data, size_t size);

int uart_write_str(char *str);

int uart_write_byte(uint8_t *byte);

struct k_msgq *uart_get_input_msgq();

struct k_msgq *uart_get_output_msgq();

#endif  // _ZT_UART_H_
