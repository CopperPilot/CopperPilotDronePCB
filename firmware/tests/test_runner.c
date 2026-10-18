/**
 * @file test_runner.c
 * @brief Unified native desktop test runner executing all unit test suites.
 */

#include "ahrs.h"
#include "hal.h"
#include "motor_mixer.h"
#include "unity.h"
#include "web_server.h"

extern void mock_hal_reset(void);

void setUp(void) {
    mock_hal_reset();
    ahrs_init(0.98f);
    motor_mixer_init();
    web_server_init();
}

void tearDown(void) {}

/* Suite 1: PID Controller Tests */
extern void test_pid_proportional_response(void);
extern void test_pid_integral_accumulation_and_anti_windup(void);
extern void test_pid_derivative_filtering(void);
extern void test_pid_reset(void);
extern void test_cascaded_axis_controller(void);

/* Suite 2: AHRS Sensor Fusion Tests */
extern void test_ahrs_initialization_from_accelerometer(void);
extern void test_ahrs_known_tilt_angle(void);
extern void test_ahrs_gyro_integration(void);
extern void test_ahrs_severe_tilt_detection(void);

/* Suite 3: Motor Mixer Tests */
extern void test_mixer_disarmed_zeroes_all_motors(void);
extern void test_mixer_armed_zero_throttle_spins_at_idle(void);
extern void test_mixer_symmetric_throttle(void);
extern void test_mixer_pitch_command(void);
extern void test_mixer_roll_command(void);
extern void test_mixer_anti_clip_headroom_limiting(void);
extern void test_mixer_battery_voltage_compensation(void);

/* Suite 4: Battery & Failsafe Tests */
extern void test_battery_adc_reading(void);
extern void test_failsafe_watchdog_normal(void);
extern void test_failsafe_watchdog_timeout(void);
extern void test_failsafe_low_voltage_thresholds(void);

int main(void) {
    UnityBegin("CopperPilot Drone Native Avionics & Control Test Suite");

    /* 1. PID Tests */
    RUN_TEST(test_pid_proportional_response);
    RUN_TEST(test_pid_integral_accumulation_and_anti_windup);
    RUN_TEST(test_pid_derivative_filtering);
    RUN_TEST(test_pid_reset);
    RUN_TEST(test_cascaded_axis_controller);

    /* 2. AHRS Tests */
    RUN_TEST(test_ahrs_initialization_from_accelerometer);
    RUN_TEST(test_ahrs_known_tilt_angle);
    RUN_TEST(test_ahrs_gyro_integration);
    RUN_TEST(test_ahrs_severe_tilt_detection);

    /* 3. Motor Mixer Tests */
    RUN_TEST(test_mixer_disarmed_zeroes_all_motors);
    RUN_TEST(test_mixer_armed_zero_throttle_spins_at_idle);
    RUN_TEST(test_mixer_symmetric_throttle);
    RUN_TEST(test_mixer_pitch_command);
    RUN_TEST(test_mixer_roll_command);
    RUN_TEST(test_mixer_anti_clip_headroom_limiting);
    RUN_TEST(test_mixer_battery_voltage_compensation);

    /* 4. Battery & Failsafe Tests */
    RUN_TEST(test_battery_adc_reading);
    RUN_TEST(test_failsafe_watchdog_normal);
    RUN_TEST(test_failsafe_watchdog_timeout);
    RUN_TEST(test_failsafe_low_voltage_thresholds);

    return UnityEnd();
}
