idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES hal avionics networking web_ui esp_timer esp_wifi esp_http_server nvs_flash cjson
)
