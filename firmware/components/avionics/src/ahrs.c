/**
 * @file ahrs.c
 * @brief Complementary filter AHRS implementation.
 */

#include "ahrs.h"

#include <math.h>

#define RAD_TO_DEG (180.0f / 3.14159265358979323846f)

static float s_alpha = AHRS_DEFAULT_ALPHA;
static ahrs_attitude_t s_attitude = {0};
static bool s_initialized = false;

void ahrs_init(float alpha) {
    s_alpha = (alpha > 0.0f && alpha < 1.0f) ? alpha : AHRS_DEFAULT_ALPHA;
    ahrs_reset();
}

void ahrs_reset(void) {
    s_attitude.roll = 0.0f;
    s_attitude.pitch = 0.0f;
    s_attitude.yaw = 0.0f;
    s_attitude.roll_rate = 0.0f;
    s_attitude.pitch_rate = 0.0f;
    s_attitude.yaw_rate = 0.0f;
    s_initialized = false;
}

void ahrs_update(const mpu6050_data_t *imu, float dt_s) {
    if (!imu || dt_s <= 0.0f)
        return;

    /* Store filtered body angular rates */
    s_attitude.roll_rate = imu->gx;
    s_attitude.pitch_rate = imu->gy;
    s_attitude.yaw_rate = imu->gz;

    /* Calculate tilt angles from accelerometer gravity vector */
    /* Roll = atan2(ay, az), Pitch = atan2(-ax, sqrt(ay^2 + az^2)) */
    float accel_roll = atan2f(imu->ay, imu->az) * RAD_TO_DEG;
    float accel_pitch = atan2f(-imu->ax, sqrtf(imu->ay * imu->ay + imu->az * imu->az)) * RAD_TO_DEG;

    if (!s_initialized) {
        /* Initialize directly from accelerometer on first valid frame */
        s_attitude.roll = accel_roll;
        s_attitude.pitch = accel_pitch;
        s_attitude.yaw = 0.0f;
        s_initialized = true;
        return;
    }

    /* Integrate gyroscope angular rates */
    float gyro_roll = s_attitude.roll + (imu->gx * dt_s);
    float gyro_pitch = s_attitude.pitch + (imu->gy * dt_s);
    s_attitude.yaw += (imu->gz * dt_s);

    /* Normalize yaw to [-180, 180] */
    while (s_attitude.yaw > 180.0f)
        s_attitude.yaw -= 360.0f;
    while (s_attitude.yaw < -180.0f)
        s_attitude.yaw += 360.0f;

    /* Complementary filter sensor fusion */
    s_attitude.roll = (s_alpha * gyro_roll) + ((1.0f - s_alpha) * accel_roll);
    s_attitude.pitch = (s_alpha * gyro_pitch) + ((1.0f - s_alpha) * accel_pitch);
}

void ahrs_get_attitude(ahrs_attitude_t *out_attitude) {
    if (out_attitude) {
        *out_attitude = s_attitude;
    }
}

bool ahrs_is_crashed_or_inverted(void) {
    return (fabsf(s_attitude.roll) > AHRS_MAX_SAFE_TILT_DEG ||
            fabsf(s_attitude.pitch) > AHRS_MAX_SAFE_TILT_DEG);
}
