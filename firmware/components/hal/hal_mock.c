/**
 * @file hal_mock.c
 * @brief Native desktop mock implementation of the Hardware Abstraction Layer.
 */

#include "hal.h"

#include <string.h>

/* Internal mock state */
static uint64_t s_mock_time_us = 1000000;
static uint16_t s_motor_pwms[4] = {0, 0, 0, 0};
static uint32_t s_battery_mv = 4000; /* 4.0V default nominal */
static bool s_boot_button_pressed = false;

/* Simulated MPU-6050 register memory */
static uint8_t s_mpu_registers[256];

/* -------------------------------------------------------------------------- */
/* Driver Implementations                                                     */
/* -------------------------------------------------------------------------- */
static uint64_t mock_get_time_us(void) {
    return s_mock_time_us;
}

static void mock_delay_ms(uint32_t ms) {
    s_mock_time_us += (uint64_t)ms * 1000ULL;
}

static void mock_delay_us(uint32_t us) {
    s_mock_time_us += (uint64_t)us;
}

static bool mock_i2c_init(uint8_t sda, uint8_t scl, uint32_t freq) {
    (void)sda;
    (void)scl;
    (void)freq;
    return true;
}

static bool mock_i2c_write(uint8_t dev_addr, uint8_t reg_addr, const uint8_t *data, size_t len) {
    (void)dev_addr;
    if (reg_addr + len <= sizeof(s_mpu_registers)) {
        memcpy(&s_mpu_registers[reg_addr], data, len);
        return true;
    }
    return false;
}

static bool mock_i2c_read(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, size_t len) {
    (void)dev_addr;
    if (reg_addr + len <= sizeof(s_mpu_registers)) {
        memcpy(data, &s_mpu_registers[reg_addr], len);
        return true;
    }
    return false;
}

static bool mock_motor_init(void) {
    memset(s_motor_pwms, 0, sizeof(s_motor_pwms));
    return true;
}

static void mock_motor_set_pwm(uint8_t channel, uint16_t duty) {
    if (channel < 4) {
        if (duty > HAL_PWM_MAX_DUTY) {
            duty = HAL_PWM_MAX_DUTY;
        }
        s_motor_pwms[channel] = duty;
    }
}

static bool mock_adc_init(void) {
    return true;
}

static uint32_t mock_adc_read_battery_mv(void) {
    return s_battery_mv;
}

static bool mock_gpio_init(void) {
    return true;
}

static bool mock_read_boot_button(void) {
    return s_boot_button_pressed;
}

/* Concrete driver table */
static const hal_driver_t s_mock_driver = {
    .get_time_us = mock_get_time_us,
    .delay_ms = mock_delay_ms,
    .delay_us = mock_delay_us,
    .i2c_init = mock_i2c_init,
    .i2c_write = mock_i2c_write,
    .i2c_read = mock_i2c_read,
    .motor_init = mock_motor_init,
    .motor_set_pwm = mock_motor_set_pwm,
    .adc_init = mock_adc_init,
    .adc_read_battery_mv = mock_adc_read_battery_mv,
    .gpio_init = mock_gpio_init,
    .read_boot_button = mock_read_boot_button,
};

const hal_driver_t *g_hal = &s_mock_driver;

void hal_set_driver(const hal_driver_t *driver) {
    g_hal = driver ? driver : &s_mock_driver;
}

/* -------------------------------------------------------------------------- */
/* Test Harness Helper Functions                                              */
/* -------------------------------------------------------------------------- */
void mock_hal_reset(void) {
    s_mock_time_us = 1000000;
    memset(s_motor_pwms, 0, sizeof(s_motor_pwms));
    s_battery_mv = 4000;
    s_boot_button_pressed = false;
    memset(s_mpu_registers, 0, sizeof(s_mpu_registers));
    s_mpu_registers[0x75] = 0x68; /* WHO_AM_I default */
    g_hal = &s_mock_driver;
}

void mock_hal_set_time_us(uint64_t time_us) {
    s_mock_time_us = time_us;
}

void mock_hal_advance_time_us(uint64_t delta_us) {
    s_mock_time_us += delta_us;
}

uint16_t mock_hal_get_motor_pwm(uint8_t channel) {
    return (channel < 4) ? s_motor_pwms[channel] : 0;
}

void mock_hal_set_battery_mv(uint32_t mv) {
    s_battery_mv = mv;
}

void mock_hal_set_boot_button(bool pressed) {
    s_boot_button_pressed = pressed;
}

void mock_hal_set_imu_raw(int16_t ax, int16_t ay, int16_t az, int16_t gx, int16_t gy, int16_t gz) {
    /* MPU-6050 burst read buffer from 0x3B (ACCEL_XOUT_H) */
    s_mpu_registers[0x3B] = (uint8_t)((ax >> 8) & 0xFF);
    s_mpu_registers[0x3C] = (uint8_t)(ax & 0xFF);
    s_mpu_registers[0x3D] = (uint8_t)((ay >> 8) & 0xFF);
    s_mpu_registers[0x3E] = (uint8_t)(ay & 0xFF);
    s_mpu_registers[0x3F] = (uint8_t)((az >> 8) & 0xFF);
    s_mpu_registers[0x40] = (uint8_t)(az & 0xFF);
    /* Temperature at 0x41, 0x42 (dummy) */
    s_mpu_registers[0x41] = 0x00;
    s_mpu_registers[0x42] = 0x00;
    /* Gyroscope */
    s_mpu_registers[0x43] = (uint8_t)((gx >> 8) & 0xFF);
    s_mpu_registers[0x44] = (uint8_t)(gx & 0xFF);
    s_mpu_registers[0x45] = (uint8_t)((gy >> 8) & 0xFF);
    s_mpu_registers[0x46] = (uint8_t)(gy & 0xFF);
    s_mpu_registers[0x47] = (uint8_t)((gz >> 8) & 0xFF);
    s_mpu_registers[0x48] = (uint8_t)(gz & 0xFF);
}
