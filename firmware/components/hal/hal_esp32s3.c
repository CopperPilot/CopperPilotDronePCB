/**
 * @file hal_esp32s3.c
 * @brief Concrete ESP32-S3 hardware driver implementation using ESP-IDF.
 */

#if defined(ESP_PLATFORM)

#include "driver/gpio.h"
#include "driver/i2c.h"
#include "driver/ledc.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "hal.h"
#include "rom/ets_sys.h"

static const char *TAG = "HAL_ESP32S3";

#define I2C_MASTER_NUM I2C_NUM_0
#define I2C_MASTER_TIMEOUT pdMS_TO_TICKS(50)

/* ADC Calibration handle */
static adc_oneshot_unit_handle_t s_adc_handle = NULL;
static adc_cali_handle_t s_adc_cali_handle = NULL;
static bool s_adc_calibrated = false;

/* -------------------------------------------------------------------------- */
/* Timing Functions                                                           */
/* -------------------------------------------------------------------------- */
static uint64_t esp32s3_get_time_us(void) {
    return (uint64_t)esp_timer_get_time();
}

static void esp32s3_delay_ms(uint32_t ms) {
    vTaskDelay(pdMS_TO_TICKS(ms));
}

static void esp32s3_delay_us(uint32_t us) {
    ets_delay_us(us);
}

/* -------------------------------------------------------------------------- */
/* I2C Master Functions                                                       */
/* -------------------------------------------------------------------------- */
static bool esp32s3_i2c_init(uint8_t sda_pin, uint8_t scl_pin, uint32_t freq_hz) {
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = sda_pin,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_io_num = scl_pin,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = freq_hz,
    };
    esp_err_t err = i2c_param_config(I2C_MASTER_NUM, &conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c_param_config failed: %s", esp_err_to_name(err));
        return false;
    }
    err = i2c_driver_install(I2C_MASTER_NUM, conf.mode, 0, 0, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c_driver_install failed: %s", esp_err_to_name(err));
        return false;
    }
    ESP_LOGI(TAG, "I2C initialized: SDA=%d, SCL=%d, Freq=%lu Hz", sda_pin, scl_pin, freq_hz);
    return true;
}

static bool esp32s3_i2c_write(uint8_t dev_addr, uint8_t reg_addr, const uint8_t *data, size_t len) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev_addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg_addr, true);
    if (len > 0 && data != NULL) {
        i2c_master_write(cmd, (uint8_t *)data, len, true);
    }
    i2c_master_stop(cmd);
    esp_err_t err = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, I2C_MASTER_TIMEOUT);
    i2c_cmd_link_delete(cmd);
    return (err == ESP_OK);
}

static bool esp32s3_i2c_read(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, size_t len) {
    if (len == 0 || data == NULL)
        return false;

    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev_addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg_addr, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev_addr << 1) | I2C_MASTER_READ, true);
    if (len > 1) {
        i2c_master_read(cmd, data, len - 1, I2C_MASTER_ACK);
    }
    i2c_master_read_byte(cmd, data + len - 1, I2C_MASTER_NACK);
    i2c_master_stop(cmd);
    esp_err_t err = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, I2C_MASTER_TIMEOUT);
    i2c_cmd_link_delete(cmd);
    return (err == ESP_OK);
}

/* -------------------------------------------------------------------------- */
/* Motor LEDC PWM Actuation                                                   */
/* -------------------------------------------------------------------------- */
static const int s_motor_gpio_map[4] = {
    HAL_PIN_MOTOR_1, /* GPIO4: RL / M1 */
    HAL_PIN_MOTOR_2, /* GPIO5: FL / M2 */
    HAL_PIN_MOTOR_3, /* GPIO6: FR / M3 */
    HAL_PIN_MOTOR_4  /* GPIO7: RR / M4 */
};

static bool esp32s3_motor_init(void) {
    ledc_timer_config_t timer_conf = {.speed_mode = LEDC_LOW_SPEED_MODE,
                                      .duty_resolution = LEDC_TIMER_10_BIT,
                                      .timer_num = LEDC_TIMER_0,
                                      .freq_hz = HAL_PWM_FREQUENCY_HZ,
                                      .clk_cfg = LEDC_AUTO_CLK};
    if (ledc_timer_config(&timer_conf) != ESP_OK) {
        ESP_LOGE(TAG, "LEDC timer config failed");
        return false;
    }

    for (int i = 0; i < 4; i++) {
        ledc_channel_config_t ch_conf = {.gpio_num = s_motor_gpio_map[i],
                                         .speed_mode = LEDC_LOW_SPEED_MODE,
                                         .channel = (ledc_channel_t)i,
                                         .intr_type = LEDC_INTR_DISABLE,
                                         .timer_sel = LEDC_TIMER_0,
                                         .duty = 0,
                                         .hpoint = 0};
        if (ledc_channel_config(&ch_conf) != ESP_OK) {
            ESP_LOGE(TAG, "LEDC channel %d config failed", i);
            return false;
        }
    }
    ESP_LOGI(TAG, "4-channel motor PWM initialized at 20 kHz (10-bit)");
    return true;
}

static void esp32s3_motor_set_pwm(uint8_t channel, uint16_t duty) {
    if (channel < 4) {
        if (duty > HAL_PWM_MAX_DUTY) {
            duty = HAL_PWM_MAX_DUTY;
        }
        ledc_set_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)channel, duty);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)channel);
    }
}

/* -------------------------------------------------------------------------- */
/* Battery Voltage Sensing via ADC1                                           */
/* -------------------------------------------------------------------------- */
static bool esp32s3_adc_init(void) {
    adc_oneshot_unit_init_cfg_t init_config = {
        .unit_id = ADC_UNIT_1,
    };
    if (adc_oneshot_new_unit(&init_config, &s_adc_handle) != ESP_OK) {
        ESP_LOGE(TAG, "ADC1 new unit failed");
        return false;
    }

    adc_oneshot_chan_cfg_t chan_config = {
        .bitwidth = ADC_BITWIDTH_12, .atten = ADC_ATTEN_DB_12, /* Full scale up to ~3.1V */
    };
    if (adc_oneshot_config_channel(s_adc_handle, ADC_CHANNEL_0, &chan_config) != ESP_OK) {
        ESP_LOGE(TAG, "ADC1 channel 0 config failed");
        return false;
    }

    adc_cali_curve_fitting_config_t cali_config = {
        .unit_id = ADC_UNIT_1,
        .chan = ADC_CHANNEL_0,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_12,
    };
    if (adc_cali_create_scheme_curve_fitting(&cali_config, &s_adc_cali_handle) == ESP_OK) {
        s_adc_calibrated = true;
    }
    ESP_LOGI(TAG, "ADC1 battery sensing initialized on GPIO1 (ADC1_CH0)");
    return true;
}

static uint32_t esp32s3_adc_read_battery_mv(void) {
    if (!s_adc_handle)
        return 0;

    int raw = 0;
    if (adc_oneshot_read(s_adc_handle, ADC_CHANNEL_0, &raw) != ESP_OK) {
        return 0;
    }

    int voltage_mv = 0;
    if (s_adc_calibrated) {
        adc_cali_raw_to_voltage(s_adc_cali_handle, raw, &voltage_mv);
    } else {
        voltage_mv = (raw * 3100) / 4095;
    }

    /* Hardware voltage divider: R27=100k, R28=100k (Ratio 1:2) */
    /* V_batt = 2.0 * V_pin */
    return (uint32_t)(voltage_mv * 2);
}

/* -------------------------------------------------------------------------- */
/* GPIO & Pushbutton Controls                                                 */
/* -------------------------------------------------------------------------- */
static bool esp32s3_gpio_init(void) {
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << HAL_PIN_BOOT_BTN) | (1ULL << HAL_PIN_MPU_INT),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    return (gpio_config(&io_conf) == ESP_OK);
}

static bool esp32s3_read_boot_button(void) {
    /* Active-low switch SW3 */
    return (gpio_get_level((gpio_num_t)HAL_PIN_BOOT_BTN) == 0);
}

/* Concrete ESP-IDF driver table */
static const hal_driver_t s_esp32s3_driver = {
    .get_time_us = esp32s3_get_time_us,
    .delay_ms = esp32s3_delay_ms,
    .delay_us = esp32s3_delay_us,
    .i2c_init = esp32s3_i2c_init,
    .i2c_write = esp32s3_i2c_write,
    .i2c_read = esp32s3_i2c_read,
    .motor_init = esp32s3_motor_init,
    .motor_set_pwm = esp32s3_motor_set_pwm,
    .adc_init = esp32s3_adc_init,
    .adc_read_battery_mv = esp32s3_adc_read_battery_mv,
    .gpio_init = esp32s3_gpio_init,
    .read_boot_button = esp32s3_read_boot_button,
};

void hal_esp32s3_init(void) {
    hal_set_driver(&s_esp32s3_driver);
    g_hal->gpio_init();
    g_hal->i2c_init(HAL_PIN_I2C_SDA, HAL_PIN_I2C_SCL, 400000);
    g_hal->motor_init();
    g_hal->adc_init();
}

#endif /* ESP_PLATFORM */
