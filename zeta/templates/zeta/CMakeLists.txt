cmake_minimum_required(VERSION 3.13)

if(CONFIG_ZETA)
  message("[ZETA]: Set Zeta as a zephyr module")
  zephyr_interface_library_named(ZETA)

  # This line is for compatibility and should be removed at some point of time.
  # It is supposed to allow building sources that still reference cbor headers
  # without tinycbor subrirectory.
  target_include_directories(ZETA INTERFACE "${CMAKE_CURRENT_LIST_DIR}/include")

  zephyr_library()
  zephyr_library_sources(src/zeta.c)
  zephyr_library_sources_ifdef(CONFIG_ZETA_SERIAL_IPC src/zt_serial_ipc.c src/zt_uart.c)

  zephyr_library_link_libraries(ZETA)
  target_link_libraries(ZETA INTERFACE zephyr_interface)
endif()
