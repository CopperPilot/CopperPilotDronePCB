/**
 * @file ahrs.h
 * @brief 6-DOF Complementary Filter Attitude and Heading Reference System.
 */

#ifndef COPPERPILOT_AHRS_H
#define COPPERPILOT_AHRS_H

#include "mpu6050.h"

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define AHRS_DEFAULT_ALPHA 0.98f     /* 500 Hz complementary filter coefficient */
#define AHRS_MAX_SAFE_TILT_DEG 60.0f /* Tilt threshold for emergency crash kill */

typedef struct {
    float roll;  /* Roll attitude in degrees (Bank right = positive) */
    float pitch; /* Pitch attitude in degrees (Nose up = positive) */
    float yaw;   /* Relative yaw in degrees (Clockwise = positive) */

    float roll_rate;  /* Filtered roll angular rate in deg/s */
    float pitch_rate; /* Filtered pitch angular rate in deg/s */
    float yaw_rate;   /* Filtered yaw angular rate in deg/s */
} ahrs_attitude_t;

void ahrs_init(float alpha);
void ahrs_reset(void);
void ahrs_update(const mpu6050_data_t *imu, float dt_s);
void ahrs_get_attitude(ahrs_attitude_t *out_attitude);
bool ahrs_is_crashed_or_inverted(void);

#ifdef __cplusplus
}
#endif

#endif /* COPPERPILOT_AHRS_H */
