/**
 * @file web_server.c
 * @brief Embedded HTTP/WebSocket server implementation.
 */

#include "web_server.h"

#include "hal.h"
#include "web_ui_data.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static flight_command_t s_command = {.roll_target_deg = 0.0f,
                                     .pitch_target_deg = 0.0f,
                                     .yaw_rate_target_dps = 0.0f,
                                     .throttle_norm = 0.0f,
                                     .arm_command = false,
                                     .emergency_stop = false,
                                     .last_packet_time_us = 0};

static flight_telemetry_t s_telemetry = {0};

void web_server_get_command(flight_command_t *out_cmd) {
    if (out_cmd) {
        *out_cmd = s_command;
    }
}

void web_server_update_telemetry(const flight_telemetry_t *telem) {
    if (telem) {
        s_telemetry = *telem;
    }
}

bool web_server_is_connection_lost(uint64_t now_us, uint32_t timeout_ms) {
    if (s_command.last_packet_time_us == 0)
        return true;
    uint64_t elapsed_us = now_us - s_command.last_packet_time_us;
    return (elapsed_us > (uint64_t)timeout_ms * 1000ULL);
}

void web_server_inject_mock_command(const flight_command_t *cmd) {
    if (cmd) {
        s_command = *cmd;
    }
}

#if defined(ESP_PLATFORM)

#include "cJSON.h"
#include "esp_http_server.h"
#include "esp_log.h"

static const char *TAG = "WEB_SERVER";
static httpd_handle_t s_server = NULL;
static int s_ws_client_fd = -1;

static esp_err_t root_get_handler(httpd_req_t *req) {
    httpd_resp_set_type(req, "text/html");
    httpd_resp_set_hdr(req, "Content-Encoding", "identity");
    return httpd_resp_send(req, g_web_ui_html, g_web_ui_html_len);
}

static esp_err_t ws_handler(httpd_req_t *req) {
    if (req->method == HTTP_GET) {
        s_ws_client_fd = httpd_req_to_sockfd(req);
        ESP_LOGI(TAG, "WebSocket client connected: fd=%d", s_ws_client_fd);
        return ESP_OK;
    }

    httpd_ws_frame_t ws_pkt;
    uint8_t rx_buf[256];
    memset(&ws_pkt, 0, sizeof(httpd_ws_frame_t));
    ws_pkt.payload = rx_buf;
    ws_pkt.type = HTTPD_WS_TYPE_TEXT;

    esp_err_t ret = httpd_ws_recv_frame(req, &ws_pkt, sizeof(rx_buf) - 1);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "httpd_ws_recv_frame failed: %d", ret);
        return ret;
    }
    rx_buf[ws_pkt.len] = '\0';

    /* Parse JSON packet: {"t":0.5,"r":0.0,"p":0.0,"y":0.0,"arm":true} */
    cJSON *root = cJSON_Parse((char *)rx_buf);
    if (root) {
        cJSON *item_em = cJSON_GetObjectItem(root, "emergency");
        if (item_em && cJSON_IsTrue(item_em)) {
            s_command.emergency_stop = true;
            s_command.arm_command = false;
            s_command.throttle_norm = 0.0f;
        } else {
            cJSON *item_t = cJSON_GetObjectItem(root, "t");
            cJSON *item_r = cJSON_GetObjectItem(root, "r");
            cJSON *item_p = cJSON_GetObjectItem(root, "p");
            cJSON *item_y = cJSON_GetObjectItem(root, "y");
            cJSON *item_arm = cJSON_GetObjectItem(root, "arm");

            if (item_t && cJSON_IsNumber(item_t))
                s_command.throttle_norm = (float)item_t->valuedouble;
            if (item_r && cJSON_IsNumber(item_r))
                s_command.roll_target_deg = (float)item_r->valuedouble;
            if (item_p && cJSON_IsNumber(item_p))
                s_command.pitch_target_deg = (float)item_p->valuedouble;
            if (item_y && cJSON_IsNumber(item_y))
                s_command.yaw_rate_target_dps = (float)item_y->valuedouble;
            if (item_arm && cJSON_IsBool(item_arm)) {
                /* Safety interlock: Only allow arming if throttle is near zero */
                if (cJSON_IsTrue(item_arm)) {
                    if (s_command.throttle_norm < 0.05f) {
                        s_command.arm_command = true;
                        s_command.emergency_stop = false;
                    }
                } else {
                    s_command.arm_command = false;
                }
            }
        }
        s_command.last_packet_time_us = hal_get_time_us();
        cJSON_Delete(root);
    }
    return ESP_OK;
}

static const httpd_uri_t uri_root = {
    .uri = "/", .method = HTTP_GET, .handler = root_get_handler, .user_ctx = NULL};

static const httpd_uri_t uri_ws = {.uri = "/ws",
                                   .method = HTTP_GET,
                                   .handler = ws_handler,
                                   .user_ctx = NULL,
                                   .is_websocket = true};

bool web_server_init(void) {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.max_open_sockets = 4;
    config.stack_size = 8192;

    ESP_LOGI(TAG, "Starting web server on port %d...", config.server_port);
    if (httpd_start(&s_server, &config) == ESP_OK) {
        httpd_register_uri_handler(s_server, &uri_root);
        httpd_register_uri_handler(s_server, &uri_ws);
        return true;
    }
    return false;
}

#else

/* Host desktop mock implementation */
bool web_server_init(void) {
    s_command.last_packet_time_us = hal_get_time_us();
    return true;
}

#endif
