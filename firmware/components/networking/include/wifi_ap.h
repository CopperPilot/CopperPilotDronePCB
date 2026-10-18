/**
 * @file wifi_ap.h
 * @brief Standalone Wi-Fi SoftAP initialization for low-latency drone telemetry and control.
 */

#ifndef COPPERPILOT_WIFI_AP_H
#define COPPERPILOT_WIFI_AP_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define DRONE_DEFAULT_SSID_PREFIX "CopperPilot-Drone-"
#define DRONE_DEFAULT_PASS "copperpilot"
#define DRONE_AP_CHANNEL 6
#define DRONE_AP_MAX_CONN 4

bool wifi_ap_init(void);
void wifi_ap_get_ssid(char *out_ssid, size_t max_len);

#ifdef __cplusplus
}
#endif

#endif /* COPPERPILOT_WIFI_AP_H */
