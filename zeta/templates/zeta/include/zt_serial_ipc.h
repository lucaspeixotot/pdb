#ifndef _ZT_SERIAL_IPC_H_
#define _ZT_SERIAL_IPC_H_

#include <zephyr.h>
#include "zeta.h"

#define ZT_SERIAL_IPC_RX_THREAD_STACK_SIZE 2048
#define ZT_SERIAL_RX_THREAD_PRIORITY 3

#define ZT_SERIAL_IPC_TX_THREAD_STACK_SIZE 2048
#define ZT_SERIAL_TX_THREAD_PRIORITY 3

int zt_serial_ipc_send_update_to_host(zt_channel_e id);

k_tid_t zt_serial_ipc_thread();

#endif  // _ZT_SERIAL_IPC_H_
