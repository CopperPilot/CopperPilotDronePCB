idf_component_register(
    SRCS
        "src/wifi_ap.c"
        "src/web_server.c"
    INCLUDE_DIRS "include"
    REQUIRES hal esp_wifi esp_http_server nvs_flash cjson web_ui
)
