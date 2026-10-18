idf_component_register(
    SRCS "hal_esp32s3.c"
    INCLUDE_DIRS "include"
    REQUIRES driver esp_timer esp_adc
)
