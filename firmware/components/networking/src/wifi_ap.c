/**
 * @file wifi_ap.c
 * @brief Wi-Fi SoftAP implementation.
 */

#include "wifi_ap.h"

#include <stdio.h>
#include <string.h>

#if defined(ESP_PLATFORM)
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_wifi.h"
#include "lwip/err.h"
#include "lwip/sys.h"
#include "nvs_flash.h"

static const char *TAG = "WIFI_AP";
static char s_ap_ssid[32] = {0};

bool wifi_ap_init(void) {
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_SOFTAP);
    snprintf(s_ap_ssid, sizeof(s_ap_ssid), "%s%02X%02X", DRONE_DEFAULT_SSID_PREFIX, mac[4], mac[5]);

    wifi_config_t wifi_config = {
        .ap =
            {
                .channel = DRONE_AP_CHANNEL,
                .password = DRONE_DEFAULT_PASS,
                .max_connection = DRONE_AP_MAX_CONN,
                .authmode = WIFI_AUTH_WPA2_PSK,
                .pmf_cfg =
                    {
                        .required = false,
                    },
            },
    };
    strncpy((char *)wifi_config.ap.ssid, s_ap_ssid, sizeof(wifi_config.ap.ssid) - 1);
    wifi_config.ap.ssid_len = strlen(s_ap_ssid);

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    /* Disable Wi-Fi power saving for minimal round-trip latency (< 3 ms) */
    esp_wifi_set_ps(WIFI_PS_NONE);

    ESP_LOGI(TAG, "Wi-Fi SoftAP broadcast started: SSID='%s', Pass='%s'", s_ap_ssid,
             DRONE_DEFAULT_PASS);
    return true;
}

void wifi_ap_get_ssid(char *out_ssid, size_t max_len) {
    if (out_ssid && max_len > 0) {
        strncpy(out_ssid, s_ap_ssid, max_len - 1);
        out_ssid[max_len - 1] = '\0';
    }
}

#else

/* Host desktop mock implementation */
static char s_ap_ssid[32] = "CopperPilot-Drone-MOCK";

bool wifi_ap_init(void) {
    return true;
}

void wifi_ap_get_ssid(char *out_ssid, size_t max_len) {
    if (out_ssid && max_len > 0) {
        strncpy(out_ssid, s_ap_ssid, max_len - 1);
        out_ssid[max_len - 1] = '\0';
    }
}

#endif
