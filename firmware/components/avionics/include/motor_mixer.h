/**
 * @file motor_mixer.h
 * @brief Quad-X brushed motor mixer with anti-clip headroom limiting and battery compensation.
 */

#ifndef COPPERPILOT_MOTOR_MIXER_H
#define COPPERPILOT_MOTOR_MIXER_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MIXER_MAX_PWM 1000    /* Maximum motor PWM command */
#define MIXER_IDLE_PWM 50     /* Minimum idle spin when armed */
#define MIXER_MIN_THROTTLE 20 /* Minimum throttle to engage active stabilization */

typedef struct {
    uint16_t m1; /* Rear-Left (CCW, GPIO4 / J2) */
    uint16_t m2; /* Front-Left (CW, GPIO5 / J5) */
    uint16_t m3; /* Front-Right (CCW, GPIO6 / J6) */
    uint16_t m4; /* Rear-Right (CW, GPIO7 / J4) */
} motor_pwm_output_t;

void motor_mixer_init(void);
void motor_mixer_compute(float throttle_norm, float roll_cmd, float pitch_cmd, float yaw_cmd,
                         uint32_t battery_mv, bool is_armed, motor_pwm_output_t *out_pwm);
void motor_mixer_apply(const motor_pwm_output_t *pwm);
void motor_mixer_emergency_stop(void);

#ifdef __cplusplus
}
#endif

#endif /* COPPERPILOT_MOTOR_MIXER_H */
