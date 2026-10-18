/**
 * @file test_ahrs.c
 * @brief Unit tests for complementary AHRS sensor fusion.
 */

#include "ahrs.h"
#include "unity.h"

#include <math.h>

#ifndef TEST_RUNNER_ALL
void setUp(void) {
    ahrs_init(0.98f);
}

void tearDown(void) {}
#endif

void test_ahrs_initialization_from_accelerometer(void) {
    mpu6050_data_t imu = {.ax = 0.0f,
                          .ay = 0.0f,
                          .az = 1.0f, /* Level gravity pointing down */
                          .gx = 0.0f,
                          .gy = 0.0f,
                          .gz = 0.0f};

    ahrs_update(&imu, 0.002f);
    ahrs_attitude_t att;
    ahrs_get_attitude(&att);

    TEST_ASSERT_FLOAT_WITHIN(0.1f, 0.0f, att.roll);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 0.0f, att.pitch);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 0.0f, att.yaw);
    TEST_ASSERT_FALSE(ahrs_is_crashed_or_inverted());
}

void test_ahrs_known_tilt_angle(void) {
    /* 30 degree pitch up: ax = -sin(30) = -0.5, az = cos(30) = 0.866 */
    mpu6050_data_t imu = {
        .ax = -0.50f, .ay = 0.0f, .az = 0.866f, .gx = 0.0f, .gy = 0.0f, .gz = 0.0f};

    ahrs_update(&imu, 0.002f);
    ahrs_attitude_t att;
    ahrs_get_attitude(&att);

    TEST_ASSERT_FLOAT_WITHIN(0.5f, 30.0f, att.pitch);
    TEST_ASSERT_FLOAT_WITHIN(0.5f, 0.0f, att.roll);
    TEST_ASSERT_FALSE(ahrs_is_crashed_or_inverted());
}

void test_ahrs_gyro_integration(void) {
    mpu6050_data_t imu_init = {
        .ax = 0.0f, .ay = 0.0f, .az = 1.0f, .gx = 0.0f, .gy = 0.0f, .gz = 0.0f};
    ahrs_update(&imu_init, 0.002f);

    /* Spin at 100 deg/s yaw for 0.5s (250 frames @ 0.002s) */
    mpu6050_data_t imu_spin = {
        .ax = 0.0f, .ay = 0.0f, .az = 1.0f, .gx = 0.0f, .gy = 0.0f, .gz = 100.0f};
    for (int i = 0; i < 250; i++) {
        ahrs_update(&imu_spin, 0.002f);
    }

    ahrs_attitude_t att;
    ahrs_get_attitude(&att);
    TEST_ASSERT_FLOAT_WITHIN(1.0f, 50.0f, att.yaw);
}

void test_ahrs_severe_tilt_detection(void) {
    /* Severe roll > 65 degrees: ay = sin(65) = 0.906, az = cos(65) = 0.422 */
    mpu6050_data_t imu_crash = {
        .ax = 0.0f, .ay = 0.906f, .az = 0.422f, .gx = 0.0f, .gy = 0.0f, .gz = 0.0f};

    ahrs_update(&imu_crash, 0.002f);
    TEST_ASSERT_TRUE(ahrs_is_crashed_or_inverted());
}

#ifndef TEST_RUNNER_ALL
int main(void) {
    UnityBegin("test_ahrs.c");
    RUN_TEST(test_ahrs_initialization_from_accelerometer);
    RUN_TEST(test_ahrs_known_tilt_angle);
    RUN_TEST(test_ahrs_gyro_integration);
    RUN_TEST(test_ahrs_severe_tilt_detection);
    return UnityEnd();
}
#endif
