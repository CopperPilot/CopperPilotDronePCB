/**
 * @file test_motor_mixer.c
 * @brief Unit tests for Quad-X motor mixing matrix and anti-clip saturation.
 */

#include "motor_mixer.h"
#include "unity.h"

#ifndef TEST_RUNNER_ALL
void setUp(void) {
    motor_mixer_init();
}

void tearDown(void) {}
#endif

void test_mixer_disarmed_zeroes_all_motors(void) {
    motor_pwm_output_t out;
    motor_mixer_compute(0.5f, 20.0f, -20.0f, 10.0f, 4000, false, &out);

    TEST_ASSERT_EQUAL_UINT(0, out.m1);
    TEST_ASSERT_EQUAL_UINT(0, out.m2);
    TEST_ASSERT_EQUAL_UINT(0, out.m3);
    TEST_ASSERT_EQUAL_UINT(0, out.m4);
}

void test_mixer_armed_zero_throttle_spins_at_idle(void) {
    motor_pwm_output_t out;
    motor_mixer_compute(0.0f, 0.0f, 0.0f, 0.0f, 4000, true, &out);

    TEST_ASSERT_EQUAL_UINT(MIXER_IDLE_PWM, out.m1);
    TEST_ASSERT_EQUAL_UINT(MIXER_IDLE_PWM, out.m2);
    TEST_ASSERT_EQUAL_UINT(MIXER_IDLE_PWM, out.m3);
    TEST_ASSERT_EQUAL_UINT(MIXER_IDLE_PWM, out.m4);
}

void test_mixer_symmetric_throttle(void) {
    motor_pwm_output_t out;
    /* 50% throttle = 500 counts */
    motor_mixer_compute(0.5f, 0.0f, 0.0f, 0.0f, 4000, true, &out);

    TEST_ASSERT_EQUAL_UINT(500, out.m1);
    TEST_ASSERT_EQUAL_UINT(500, out.m2);
    TEST_ASSERT_EQUAL_UINT(500, out.m3);
    TEST_ASSERT_EQUAL_UINT(500, out.m4);
}

void test_mixer_pitch_command(void) {
    motor_pwm_output_t out;
    /* Base 500, pitch +50 (nose up) -> rear motors (M1, M4) speed up, front (M2, M3) slow down */
    motor_mixer_compute(0.5f, 0.0f, 50.0f, 0.0f, 4000, true, &out);

    TEST_ASSERT_EQUAL_UINT(550, out.m1); /* Rear-Left */
    TEST_ASSERT_EQUAL_UINT(450, out.m2); /* Front-Left */
    TEST_ASSERT_EQUAL_UINT(450, out.m3); /* Front-Right */
    TEST_ASSERT_EQUAL_UINT(550, out.m4); /* Rear-Right */
}

void test_mixer_roll_command(void) {
    motor_pwm_output_t out;
    /* Base 500, roll +50 (bank right) -> left motors (M1, M2) speed up, right (M3, M4) slow down */
    motor_mixer_compute(0.5f, 50.0f, 0.0f, 0.0f, 4000, true, &out);

    TEST_ASSERT_EQUAL_UINT(550, out.m1); /* Rear-Left */
    TEST_ASSERT_EQUAL_UINT(550, out.m2); /* Front-Left */
    TEST_ASSERT_EQUAL_UINT(450, out.m3); /* Front-Right */
    TEST_ASSERT_EQUAL_UINT(450, out.m4); /* Rear-Right */
}

void test_mixer_anti_clip_headroom_limiting(void) {
    motor_pwm_output_t out;
    /* Base 950 + Roll 100 -> M1 = 1050 > 1000! Excess = 50 subtracted from all */
    motor_mixer_compute(0.95f, 100.0f, 0.0f, 0.0f, 4000, true, &out);

    TEST_ASSERT_EQUAL_UINT(1000, out.m1);
    TEST_ASSERT_EQUAL_UINT(1000, out.m2);
    TEST_ASSERT_EQUAL_UINT(800, out.m3);
    TEST_ASSERT_EQUAL_UINT(800, out.m4);
}

void test_mixer_battery_voltage_compensation(void) {
    motor_pwm_output_t out_nom;
    motor_pwm_output_t out_sag;

    /* At 4.0V nominal, 50% throttle = 500 */
    motor_mixer_compute(0.5f, 0.0f, 0.0f, 0.0f, 4000, true, &out_nom);
    /* At 3.6V sagged, duty cycle scales up by (4.0/3.6)^2 = 1.234 -> ~617 */
    motor_mixer_compute(0.5f, 0.0f, 0.0f, 0.0f, 3600, true, &out_sag);

    TEST_ASSERT_EQUAL_UINT(500, out_nom.m1);
    TEST_ASSERT_TRUE(out_sag.m1 > out_nom.m1);
    TEST_ASSERT_FLOAT_WITHIN(10.0f, 617.0f, (float)out_sag.m1);
}

#ifndef TEST_RUNNER_ALL
int main(void) {
    UnityBegin("test_motor_mixer.c");
    RUN_TEST(test_mixer_disarmed_zeroes_all_motors);
    RUN_TEST(test_mixer_armed_zero_throttle_spins_at_idle);
    RUN_TEST(test_mixer_symmetric_throttle);
    RUN_TEST(test_mixer_pitch_command);
    RUN_TEST(test_mixer_roll_command);
    RUN_TEST(test_mixer_anti_clip_headroom_limiting);
    RUN_TEST(test_mixer_battery_voltage_compensation);
    return UnityEnd();
}
#endif
