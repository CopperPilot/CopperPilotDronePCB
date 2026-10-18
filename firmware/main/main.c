/**
 * @file main.c
 * @brief Application entry point and FreeRTOS dual-core flight task scheduler.
 */

#include "ahrs.h"
#include "hal.h"
#include "motor_mixer.h"
#include "mpu6050.h"
#include "pid.h"
#include "web_server.h"
#include "wifi_ap.h"

#include <stdbool.h>
#include <stdio.h>

#if defined(ESP_PLATFORM)
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "DRONE_MAIN";

/* Global avionics state */
static cascaded_axis_controller_t s_roll_ctrl;
static cascaded_axis_controller_t s_pitch_ctrl;
static pid_controller_t s_yaw_ctrl;

static volatile bool s_is_armed = false;
static uint32_t s_battery_mv = 4000;

/* -------------------------------------------------------------------------- */
/* Core 1: Time-Critical Avionics Stabilization Loop (500 Hz, 2.0 ms period)  */
/* -------------------------------------------------------------------------- */
static void avionics_task(void *pvParameters) {
    (void)pvParameters;
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period_ticks = pdMS_TO_TICKS(2); /* 500 Hz */
    const float dt_s = 0.002f;

    ESP_LOGI(TAG, "Avionics Core 1 task running at 500 Hz");

    uint8_t angle_divider = 0;
    float roll_cmd = 0.0f;
    float pitch_cmd = 0.0f;

    while (1) {
        vTaskDelayUntil(&last_wake_time, period_ticks);

        /* 1. Burst read 14 bytes from MPU-6050 */
        mpu6050_data_t imu;
        if (!mpu6050_read_data(&imu)) {
            continue;
        }

        /* 2. AHRS Sensor Fusion */
        ahrs_update(&imu, dt_s);
        ahrs_attitude_t att;
        ahrs_get_attitude(&att);

        /* 3. Fetch latest command setpoints from Core 0 */
        flight_command_t cmd;
        web_server_get_command(&cmd);

        /* 4. Safety Failsafe Checks */
        uint64_t now_us = hal_get_time_us();

        /* Failsafe 1: Severe tilt / crash inversion (> 60 deg) */
        if (ahrs_is_crashed_or_inverted()) {
            s_is_armed = false;
        }

        /* Failsafe 2: Packet loss watchdog */
        if (web_server_is_connection_lost(now_us, 500)) {
            s_is_armed = false; /* Total radio loss -> kill motors */
        } else if (web_server_is_connection_lost(now_us, 300)) {
            /* Transient glitch -> auto-descent */
            cmd.throttle_norm = 0.15f;
            cmd.roll_target_deg = 0.0f;
            cmd.pitch_target_deg = 0.0f;
        }

        /* Failsafe 3: Low voltage cutoff (< 3.3V) */
        if (s_battery_mv < 3300 && s_battery_mv > 2000) {
            s_is_armed = false;
        }

        /* Handle Arming / Disarming Transitions */
        if (cmd.emergency_stop) {
            s_is_armed = false;
        } else if (cmd.arm_command && !s_is_armed) {
            /* Arming safety interlock: level flight and zero throttle */
            if (fabsf(att.roll) < 10.0f && fabsf(att.pitch) < 10.0f && cmd.throttle_norm < 0.05f) {
                s_is_armed = true;
                cascaded_axis_reset(&s_roll_ctrl);
                cascaded_axis_reset(&s_pitch_ctrl);
                pid_reset(&s_yaw_ctrl);
            }
        } else if (!cmd.arm_command && s_is_armed) {
            s_is_armed = false;
        }

        /* 5. Cascaded PID Control */
        if (s_is_armed && cmd.throttle_norm > 0.02f) {
            /* Outer Angle Loop runs at 250 Hz (every 2nd frame) */
            angle_divider++;
            if (angle_divider >= 2) {
                angle_divider = 0;
                roll_cmd = cascaded_axis_update(&s_roll_ctrl, cmd.roll_target_deg, att.roll,
                                                att.roll_rate, dt_s * 2.0f);
                pitch_cmd = cascaded_axis_update(&s_pitch_ctrl, cmd.pitch_target_deg, att.pitch,
                                                 att.pitch_rate, dt_s * 2.0f);
            }

            /* Inner Yaw Rate Loop runs at 500 Hz */
            float yaw_cmd = pid_update(&s_yaw_ctrl, cmd.yaw_rate_target_dps, att.yaw_rate, dt_s);

            /* 6. Quad-X Motor Mixing */
            motor_pwm_output_t pwms;
            motor_mixer_compute(cmd.throttle_norm, roll_cmd, pitch_cmd, yaw_cmd, s_battery_mv, true,
                                &pwms);
            motor_mixer_apply(&pwms);
        } else {
            motor_mixer_emergency_stop();
        }
    }
}

/* -------------------------------------------------------------------------- */
/* Core 0: Networking & Housekeeping Task (50 Hz, 20 ms period)               */
/* -------------------------------------------------------------------------- */
static void networking_task(void *pvParameters) {
    (void)pvParameters;
    TickType_t last_wake = xTaskGetTickCount();
    const TickType_t period_ticks = pdMS_TO_TICKS(20); /* 50 Hz */

    uint32_t adc_accum = 0;
    uint8_t adc_samples = 0;

    while (1) {
        vTaskDelayUntil(&last_wake, period_ticks);

        /* 1. Oversample Battery ADC */
        uint32_t sample = hal_adc_read_battery_mv();
        if (sample > 2000 && sample < 4500) {
            adc_accum += sample;
            adc_samples++;
            if (adc_samples >= 10) {
                s_battery_mv = adc_accum / 10;
                adc_accum = 0;
                adc_samples = 0;
            }
        }

        /* 2. Stream 50 Hz Telemetry */
        ahrs_attitude_t att;
        ahrs_get_attitude(&att);

        flight_telemetry_t telem = {
            .roll_deg = att.roll,
            .pitch_deg = att.pitch,
            .yaw_deg = att.yaw,
            .battery_mv = s_battery_mv,
            .battery_pct = (s_battery_mv > 3300) ? (uint8_t)((s_battery_mv - 3300) / 9) : 0,
            .is_armed = s_is_armed,
            .failsafe_triggered = !s_is_armed};
        web_server_update_telemetry(&telem);
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "=== CopperPilot Drone Flight Controller Booting ===");

    /* 1. Initialize Hardware Abstraction Layer */
    extern void hal_esp32s3_init(void);
    hal_esp32s3_init();

    /* 2. Initialize Avionics Subsystems */
    if (!mpu6050_init()) {
        ESP_LOGE(TAG, "FATAL: MPU-6050 initialization failed on I2C (GPIO8/GPIO9)");
    } else {
        ESP_LOGI(TAG, "MPU-6050 initialized. Calibrating gyro bias (500 samples)...");
        mpu6050_calibrate_gyro(500);
        ESP_LOGI(TAG, "Gyro calibration complete");
    }

    ahrs_init(AHRS_DEFAULT_ALPHA);
    motor_mixer_init();

    /* 3. Initialize PID Controllers */
    /* Roll: Angle Kp=4.5, Rate Kp=1.2, Ki=0.05, Kd=0.015 */
    cascaded_axis_init(&s_roll_ctrl, 4.5f, 0.0f, 180.0f, 1.2f, 0.05f, 0.015f, 200.0f, 400.0f);
    /* Pitch: Angle Kp=4.5, Rate Kp=1.2, Ki=0.05, Kd=0.015 */
    cascaded_axis_init(&s_pitch_ctrl, 4.5f, 0.0f, 180.0f, 1.2f, 0.05f, 0.015f, 200.0f, 400.0f);
    /* Yaw: Rate Kp=2.0, Ki=0.10, Kd=0.0 */
    pid_init(&s_yaw_ctrl, 2.0f, 0.10f, 0.0f, 150.0f, 300.0f, 30.0f);

    /* 4. Start Wi-Fi SoftAP and Asynchronous Web Server */
    wifi_ap_init();
    web_server_init();

    /* 5. Pin Tasks to ESP32-S3 Cores */
    xTaskCreatePinnedToCore(avionics_task, "avionics_task", 4096, NULL, 5, NULL, 1);
    xTaskCreatePinnedToCore(networking_task, "networking_task", 4096, NULL, 2, NULL, 0);

    ESP_LOGI(TAG, "Flight controller initialized successfully. Ready to arm.");
}

#else

/* Desktop host entry point for compilation checks */
int main(void) {
    printf("CopperPilot Drone Flight Controller (Host Simulation Build)\n");
    return 0;
}

#endif
