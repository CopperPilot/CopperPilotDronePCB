/**
 * @file mpu6050.h
 * @brief High-speed MPU-6050 I2C driver with coordinate remapping and bias calibration.
 */

#ifndef COPPERPILOT_MPU6050_H
#define COPPERPILOT_MPU6050_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MPU6050_I2C_ADDR 0x68 /* AD0 tied to GND via R13 */

/* Scale factors */
#define MPU6050_ACCEL_SCALE_8G 4096.0f /* LSB / g */
#define MPU6050_GYRO_SCALE_2000 16.4f  /* LSB / (deg/s) */
#define GRAVITY_MSS 9.80665f

typedef struct {
    /* Calibrated physical measurements in body frame */
    float ax; /* Forward acceleration in g */
    float ay; /* Rightward acceleration in g */
    float az; /* Downward / vertical acceleration in g */

    float gx; /* Roll angular rate in deg/s */
    float gy; /* Pitch angular rate in deg/s */
    float gz; /* Yaw angular rate in deg/s */

    float temperature_c; /* Internal die temperature */
} mpu6050_data_t;

typedef struct {
    float bias_gx;
    float bias_gy;
    float bias_gz;
    bool is_calibrated;
} mpu6050_calib_t;

bool mpu6050_init(void);
bool mpu6050_calibrate_gyro(uint16_t sample_count);
bool mpu6050_read_data(mpu6050_data_t *out_data);

/* Direct bias getters/setters for test harness */
void mpu6050_set_gyro_bias(float bx, float by, float bz);
void mpu6050_get_gyro_bias(float *bx, float *by, float *bz);

#ifdef __cplusplus
}
#endif

#endif /* COPPERPILOT_MPU6050_H */
