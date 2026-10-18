/**
 * @file web_server.h
 * @brief Embedded HTTP and WebSocket server for responsive drone teleoperation.
 */

#ifndef COPPERPILOT_WEB_SERVER_H
#define COPPERPILOT_WEB_SERVER_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float roll_deg;
    float pitch_deg;
    float yaw_deg;
    uint32_t battery_mv;
    uint8_t battery_pct;
    uint16_t m1_pwm;
    uint16_t m2_pwm;
    uint16_t m3_pwm;
    uint16_t m4_pwm;
    bool is_armed;
    bool failsafe_triggered;
} flight_telemetry_t;

typedef struct {
    float roll_target_deg;     /* Clamped to [-30, +30] deg */
    float pitch_target_deg;    /* Clamped to [-30, +30] deg */
    float yaw_rate_target_dps; /* Clamped to [-180, +180] deg/s */
    float throttle_norm;       /* Clamped to [0.0, 1.0] */
    bool arm_command;          /* True = Request armed state */
    bool emergency_stop;       /* True = Immediate hard shutdown */
    uint64_t last_packet_time_us;
} flight_command_t;

bool web_server_init(void);
void web_server_get_command(flight_command_t *out_cmd);
void web_server_update_telemetry(const flight_telemetry_t *telem);

/* Failsafe evaluation */
bool web_server_is_connection_lost(uint64_t now_us, uint32_t timeout_ms);
void web_server_inject_mock_command(const flight_command_t *cmd);

#ifdef __cplusplus
}
#endif

#endif /* COPPERPILOT_WEB_SERVER_H */
