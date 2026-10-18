/**
 * @file test_pid.c
 * @brief Unit tests for PID and cascaded axis controllers.
 */

#include "pid.h"
#include "unity.h"

#include <math.h>

#ifndef TEST_RUNNER_ALL
void setUp(void) {}
void tearDown(void) {}
#endif

void test_pid_proportional_response(void) {
    pid_controller_t pid;
    pid_init(&pid, 2.0f, 0.0f, 0.0f, 100.0f, 200.0f, 30.0f);

    /* Zero error -> Zero output */
    float out0 = pid_update(&pid, 10.0f, 10.0f, 0.01f);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, out0);

    /* Step error = +5.0 -> Output = 2.0 * 5.0 = 10.0 */
    float out1 = pid_update(&pid, 15.0f, 10.0f, 0.01f);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 10.0f, out1);
}

void test_pid_integral_accumulation_and_anti_windup(void) {
    pid_controller_t pid;
    /* Kp=0, Ki=1.0, i_max=50.0 */
    pid_init(&pid, 0.0f, 1.0f, 0.0f, 50.0f, 100.0f, 30.0f);

    /* Error = 10.0, dt = 1.0s -> integrator increases by 10 */
    pid_update(&pid, 10.0f, 0.0f, 1.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 10.0f, pid.integrator);

    /* Accumulate past limit: 10 * 10 = 100, clamped to 50 */
    for (int i = 0; i < 10; i++) {
        pid_update(&pid, 10.0f, 0.0f, 1.0f);
    }
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 50.0f, pid.integrator);
}

void test_pid_derivative_filtering(void) {
    pid_controller_t pid;
    pid_init(&pid, 0.0f, 0.0f, 0.1f, 100.0f, 100.0f, 30.0f);

    /* First frame initializes prev_error without D spike */
    float out0 = pid_update(&pid, 0.0f, 0.0f, 0.002f);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, out0);

    /* Sudden step error */
    float out1 = pid_update(&pid, 10.0f, 0.0f, 0.002f);
    TEST_ASSERT_TRUE(out1 > 0.0f);
}

void test_pid_reset(void) {
    pid_controller_t pid;
    pid_init(&pid, 1.0f, 1.0f, 1.0f, 100.0f, 100.0f, 30.0f);
    pid_update(&pid, 50.0f, 0.0f, 0.1f);
    TEST_ASSERT_TRUE(pid.integrator > 0.0f);

    pid_reset(&pid);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, pid.integrator);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, pid.prev_error);
    TEST_ASSERT_FALSE(pid.has_prev);
}

void test_cascaded_axis_controller(void) {
    cascaded_axis_controller_t axis;
    /* Angle: Kp=4.0, Ki=0, Rate: Kp=1.0, Ki=0, Kd=0 */
    cascaded_axis_init(&axis, 4.0f, 0.0f, 100.0f, 1.0f, 0.0f, 0.0f, 50.0f, 100.0f);

    /* Target angle = 10 deg, measured angle = 0 deg -> rate setpoint = 40 dps */
    /* Measured rate = 0 dps -> rate error = 40 dps -> torque = 40 */
    float torque = cascaded_axis_update(&axis, 10.0f, 0.0f, 0.0f, 0.002f);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 40.0f, torque);
}

#ifndef TEST_RUNNER_ALL
int main(void) {
    UnityBegin("test_pid.c");
    RUN_TEST(test_pid_proportional_response);
    RUN_TEST(test_pid_integral_accumulation_and_anti_windup);
    RUN_TEST(test_pid_derivative_filtering);
    RUN_TEST(test_pid_reset);
    RUN_TEST(test_cascaded_axis_controller);
    return UnityEnd();
}
#endif
