/**
 * @file hal.h
 * @brief Hardware Abstraction Layer interface for CopperPilot Drone.
 *
 * Decouples flight avionics and networking algorithms from the underlying
 * hardware platform, enabling seamless native desktop unit testing.
 */

#ifndef COPPERPILOT_HAL_H
#define COPPERPILOT_HAL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* -------------------------------------------------------------------------- */
/* Hardware Configuration & Pin Mappings                                      */
/* -------------------------------------------------------------------------- */
#define HAL_PIN_BATTERY_ADC 1 /* GPIO1: ADC1_CH0 via 100k/100k divider */
#define HAL_PIN_MOTOR_1 4     /* GPIO4: Rear-Left Motor (T1, SI2302DS, CCW) */
#define HAL_PIN_MOTOR_2 5     /* GPIO5: Front-Left Motor (T2, SI2302DS, CW) */
#define HAL_PIN_MOTOR_3 6     /* GPIO6: Front-Right Motor (T3, SI2302DS, CCW) */
#define HAL_PIN_MOTOR_4 7     /* GPIO7: Rear-Right Motor (T4, SI2302DS, CW) */
#define HAL_PIN_I2C_SDA 8     /* GPIO8: MPU-6050 SDA (4.7k pull-up) */
#define HAL_PIN_I2C_SCL 9     /* GPIO9: MPU-6050 SCL (4.7k pull-up) */
#define HAL_PIN_MPU_INT 10    /* GPIO10: MPU-6050 Data Ready Interrupt */
#define HAL_PIN_BOOT_BTN 0    /* GPIO0: Momentary Boot Switch SW3 */

#define HAL_PWM_FREQUENCY_HZ 20000 /* 20 kHz ultrasonic PWM */
#define HAL_PWM_MAX_DUTY 1023      /* 10-bit PWM resolution (0..1023) */

/* -------------------------------------------------------------------------- */
/* HAL Function Pointer Interface                                             */
/* -------------------------------------------------------------------------- */
typedef struct {
    /* Timing */
    uint64_t (*get_time_us)(void);
    void (*delay_ms)(uint32_t ms);
    void (*delay_us)(uint32_t us);

    /* I2C Master (MPU-6050) */
    bool (*i2c_init)(uint8_t sda_pin, uint8_t scl_pin, uint32_t freq_hz);
    bool (*i2c_write)(uint8_t dev_addr, uint8_t reg_addr, const uint8_t *data, size_t len);
    bool (*i2c_read)(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, size_t len);

    /* Motor PWM Actuation */
    bool (*motor_init)(void);
    void (*motor_set_pwm)(uint8_t channel, uint16_t duty);

    /* Battery ADC */
    bool (*adc_init)(void);
    uint32_t (*adc_read_battery_mv)(void);

    /* Status LED & User Controls */
    bool (*gpio_init)(void);
    bool (*read_boot_button)(void);
} hal_driver_t;

/* Global driver pointer */
extern const hal_driver_t *g_hal;

/* Helper macros for brevity */
#define hal_get_time_us() (g_hal->get_time_us())
#define hal_delay_ms(ms) (g_hal->delay_ms(ms))
#define hal_delay_us(us) (g_hal->delay_us(us))
#define hal_i2c_write(a, r, d, l) (g_hal->i2c_write(a, r, d, l))
#define hal_i2c_read(a, r, d, l) (g_hal->i2c_read(a, r, d, l))
#define hal_motor_set_pwm(c, d) (g_hal->motor_set_pwm(c, d))
#define hal_adc_read_battery_mv() (g_hal->adc_read_battery_mv())
#define hal_read_boot_button() (g_hal->read_boot_button())

void hal_set_driver(const hal_driver_t *driver);

#ifdef __cplusplus
}
#endif

#endif /* COPPERPILOT_HAL_H */
