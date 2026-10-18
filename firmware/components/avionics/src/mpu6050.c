/**
 * @file mpu6050.c
 * @brief MPU-6050 driver implementation.
 */

#include "mpu6050.h"

#include "hal.h"

#include <string.h>

/* MPU-6050 Register Map */
#define REG_SMPLRT_DIV 0x19
#define REG_CONFIG 0x1A
#define REG_GYRO_CONFIG 0x1B
#define REG_ACCEL_CONFIG 0x1C
#define REG_INT_ENABLE 0x38
#define REG_ACCEL_XOUT_H 0x3B
#define REG_PWR_MGMT_1 0x6B
#define REG_WHO_AM_I 0x75

static mpu6050_calib_t s_calib = {
    .bias_gx = 0.0f, .bias_gy = 0.0f, .bias_gz = 0.0f, .is_calibrated = false};

bool mpu6050_init(void) {
    uint8_t who_am_i = 0;
    if (!hal_i2c_read(MPU6050_I2C_ADDR, REG_WHO_AM_I, &who_am_i, 1)) {
        return false;
    }
    if (who_am_i != 0x68 && who_am_i != 0x70 && who_am_i != 0x72) {
        return false;
    }

    /* 1. Wake up device and select internal PLL with X-axis gyro reference */
    uint8_t pwr = 0x01;
    if (!hal_i2c_write(MPU6050_I2C_ADDR, REG_PWR_MGMT_1, &pwr, 1))
        return false;
    hal_delay_ms(10);

    /* 2. Sample rate divider: 1 kHz / (1 + 0) = 1 kHz */
    uint8_t smpl = 0x00;
    if (!hal_i2c_write(MPU6050_I2C_ADDR, REG_SMPLRT_DIV, &smpl, 1))
        return false;

    /* 3. DLPF set to 42 Hz bandwidth to filter coreless motor commutation harmonics */
    uint8_t cfg = 0x03;
    if (!hal_i2c_write(MPU6050_I2C_ADDR, REG_CONFIG, &cfg, 1))
        return false;

    /* 4. Gyroscope full scale: +/- 2000 deg/s */
    uint8_t gyro_cfg = 0x18;
    if (!hal_i2c_write(MPU6050_I2C_ADDR, REG_GYRO_CONFIG, &gyro_cfg, 1))
        return false;

    /* 5. Accelerometer full scale: +/- 8g */
    uint8_t accel_cfg = 0x10;
    if (!hal_i2c_write(MPU6050_I2C_ADDR, REG_ACCEL_CONFIG, &accel_cfg, 1))
        return false;

    /* 6. Enable Data Ready interrupt on GPIO10 */
    uint8_t int_en = 0x01;
    if (!hal_i2c_write(MPU6050_I2C_ADDR, REG_INT_ENABLE, &int_en, 1))
        return false;

    return true;
}

bool mpu6050_calibrate_gyro(uint16_t sample_count) {
    if (sample_count == 0)
        return false;

    float sum_gx = 0.0f;
    float sum_gy = 0.0f;
    float sum_gz = 0.0f;

    for (uint16_t i = 0; i < sample_count; i++) {
        mpu6050_data_t raw;
        /* Temporarily zero bias for raw measurement */
        s_calib.bias_gx = 0.0f;
        s_calib.bias_gy = 0.0f;
        s_calib.bias_gz = 0.0f;

        if (!mpu6050_read_data(&raw)) {
            return false;
        }
        sum_gx += raw.gx;
        sum_gy += raw.gy;
        sum_gz += raw.gz;
        hal_delay_ms(2);
    }

    s_calib.bias_gx = sum_gx / (float)sample_count;
    s_calib.bias_gy = sum_gy / (float)sample_count;
    s_calib.bias_gz = sum_gz / (float)sample_count;
    s_calib.is_calibrated = true;
    return true;
}

bool mpu6050_read_data(mpu6050_data_t *out_data) {
    if (!out_data)
        return false;

    uint8_t buf[14];
    if (!hal_i2c_read(MPU6050_I2C_ADDR, REG_ACCEL_XOUT_H, buf, 14)) {
        return false;
    }

    int16_t raw_ax = (int16_t)((buf[0] << 8) | buf[1]);
    int16_t raw_ay = (int16_t)((buf[2] << 8) | buf[3]);
    int16_t raw_az = (int16_t)((buf[4] << 8) | buf[5]);
    int16_t raw_temp = (int16_t)((buf[6] << 8) | buf[7]);
    int16_t raw_gx = (int16_t)((buf[8] << 8) | buf[9]);
    int16_t raw_gy = (int16_t)((buf[10] << 8) | buf[11]);
    int16_t raw_gz = (int16_t)((buf[12] << 8) | buf[13]);

    /* Raw engineering units */
    float ax_g = (float)raw_ax / MPU6050_ACCEL_SCALE_8G;
    float ay_g = (float)raw_ay / MPU6050_ACCEL_SCALE_8G;
    float az_g = (float)raw_az / MPU6050_ACCEL_SCALE_8G;

    float gx_dps = (float)raw_gx / MPU6050_GYRO_SCALE_2000;
    float gy_dps = (float)raw_gy / MPU6050_GYRO_SCALE_2000;
    float gz_dps = (float)raw_gz / MPU6050_GYRO_SCALE_2000;

    /* ---------------------------------------------------------------------- */
    /* Coordinate Remapping for 180° PCB Layout Mounting                     */
    /* Drone Frame: Forward=+X, Right=+Y, Down=+Z                            */
    /* Roll: Positive right down, Pitch: Positive nose up, Yaw: Clockwise    */
    /* ---------------------------------------------------------------------- */
    out_data->ax = -ay_g;
    out_data->ay = -ax_g;
    out_data->az = az_g;

    out_data->gx = (-gx_dps) - s_calib.bias_gx;
    out_data->gy = (-gy_dps) - s_calib.bias_gy;
    out_data->gz = gz_dps - s_calib.bias_gz;

    out_data->temperature_c = ((float)raw_temp / 340.0f) + 36.53f;
    return true;
}

void mpu6050_set_gyro_bias(float bx, float by, float bz) {
    s_calib.bias_gx = bx;
    s_calib.bias_gy = by;
    s_calib.bias_gz = bz;
    s_calib.is_calibrated = true;
}

void mpu6050_get_gyro_bias(float *bx, float *by, float *bz) {
    if (bx)
        *bx = s_calib.bias_gx;
    if (by)
        *by = s_calib.bias_gy;
    if (bz)
        *bz = s_calib.bias_gz;
}
