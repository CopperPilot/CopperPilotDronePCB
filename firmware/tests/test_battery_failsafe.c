/**
 * @file test_battery_failsafe.c
 * @brief Unit tests for battery voltage monitoring and telemetry failsafes.
 */

#include "hal.h"
#include "unity.h"
#include "web_server.h"

extern void mock_hal_reset(void);
extern void mock_hal_set_time_us(uint64_t time_us);
extern void mock_hal_advance_time_us(uint64_t delta_us);
extern void mock_hal_set_battery_mv(uint32_t mv);

#ifndef TEST_RUNNER_ALL
void setUp(void) {
    mock_hal_reset();
    web_server_init();
}

void tearDown(void) {}
#endif

void test_battery_adc_reading(void) {
    mock_hal_set_battery_mv(3850);
    uint32_t v = hal_adc_read_battery_mv();
    TEST_ASSERT_EQUAL_UINT(3850, v);
}

void test_failsafe_watchdog_normal(void) {
    mock_hal_set_time_us(1000000);
    flight_command_t cmd = {.throttle_norm = 0.5f,
                            .arm_command = true,
                            .emergency_stop = false,
                            .last_packet_time_us = 1000000};
    web_server_inject_mock_command(&cmd);

    /* 100 ms later: link still valid */
    mock_hal_advance_time_us(100000);
    uint64_t now = hal_get_time_us();
    TEST_ASSERT_FALSE(web_server_is_connection_lost(now, 500));
}

void test_failsafe_watchdog_timeout(void) {
    mock_hal_set_time_us(1000000);
    flight_command_t cmd = {.throttle_norm = 0.5f,
                            .arm_command = true,
                            .emergency_stop = false,
                            .last_packet_time_us = 1000000};
    web_server_inject_mock_command(&cmd);

    /* Advance by 550 ms (> 500 ms timeout) */
    mock_hal_advance_time_us(550000);
    uint64_t now = hal_get_time_us();
    TEST_ASSERT_TRUE(web_server_is_connection_lost(now, 500));
}

void test_failsafe_low_voltage_thresholds(void) {
    /* Safe voltage */
    mock_hal_set_battery_mv(3800);
    uint32_t v_safe = hal_adc_read_battery_mv();
    TEST_ASSERT_TRUE(v_safe >= 3500);

    /* Warning threshold */
    mock_hal_set_battery_mv(3450);
    uint32_t v_warn = hal_adc_read_battery_mv();
    TEST_ASSERT_TRUE(v_warn < 3500 && v_warn >= 3300);

    /* Cutoff threshold */
    mock_hal_set_battery_mv(3250);
    uint32_t v_cutoff = hal_adc_read_battery_mv();
    TEST_ASSERT_TRUE(v_cutoff < 3300);
}

#ifndef TEST_RUNNER_ALL
int main(void) {
    UnityBegin("test_battery_failsafe.c");
    RUN_TEST(test_battery_adc_reading);
    RUN_TEST(test_failsafe_watchdog_normal);
    RUN_TEST(test_failsafe_watchdog_timeout);
    RUN_TEST(test_failsafe_low_voltage_thresholds);
    return UnityEnd();
}
#endif
