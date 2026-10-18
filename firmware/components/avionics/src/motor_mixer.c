/**
 * @file motor_mixer.c
 * @brief Quad-X brushed motor mixer implementation.
 */

#include "motor_mixer.h"

#include "hal.h"

#include <string.h>

#define NOMINAL_BATTERY_MV 4000.0f

void motor_mixer_init(void) {
    motor_mixer_emergency_stop();
}

void motor_mixer_compute(float throttle_norm, float roll_cmd, float pitch_cmd, float yaw_cmd,
                         uint32_t battery_mv, bool is_armed, motor_pwm_output_t *out_pwm) {
    if (!out_pwm)
        return;

    if (!is_armed) {
        out_pwm->m1 = 0;
        out_pwm->m2 = 0;
        out_pwm->m3 = 0;
        out_pwm->m4 = 0;
        return;
    }

    /* Clamp throttle input [0.0, 1.0] */
    if (throttle_norm < 0.0f)
        throttle_norm = 0.0f;
    if (throttle_norm > 1.0f)
        throttle_norm = 1.0f;

    /* Base throttle scaled to PWM range */
    float base_throttle = throttle_norm * (float)MIXER_MAX_PWM;

    /* Battery voltage sag compensation factor (1.0 to 1.35) */
    float v_comp = 1.0f;
    if (battery_mv > 3000 && battery_mv < 4350) {
        float ratio = NOMINAL_BATTERY_MV / (float)battery_mv;
        v_comp = ratio * ratio; /* Thrust scales as V^2 */
        if (v_comp < 1.0f)
            v_comp = 1.0f;
        if (v_comp > 1.35f)
            v_comp = 1.35f;
    }

    /* If throttle is at absolute zero, spin at gentle idle */
    if (base_throttle < (float)MIXER_MIN_THROTTLE) {
        out_pwm->m1 = MIXER_IDLE_PWM;
        out_pwm->m2 = MIXER_IDLE_PWM;
        out_pwm->m3 = MIXER_IDLE_PWM;
        out_pwm->m4 = MIXER_IDLE_PWM;
        return;
    }

    /* Apply battery compensation to base throttle */
    base_throttle *= v_comp;

    /* ---------------------------------------------------------------------- */
    /* Quad-X Mixer Equations                                                 */
    /* M1: Rear-Left   (CCW) = Throttle + Pitch + Roll + Yaw                  */
    /* M2: Front-Left  (CW)  = Throttle - Pitch + Roll - Yaw                  */
    /* M3: Front-Right (CCW) = Throttle - Pitch - Roll + Yaw                  */
    /* M4: Rear-Right  (CW)  = Throttle + Pitch - Roll - Yaw                  */
    /* ---------------------------------------------------------------------- */
    float m1 = base_throttle + pitch_cmd + roll_cmd + yaw_cmd;
    float m2 = base_throttle - pitch_cmd + roll_cmd - yaw_cmd;
    float m3 = base_throttle - pitch_cmd - roll_cmd + yaw_cmd;
    float m4 = base_throttle + pitch_cmd - roll_cmd - yaw_cmd;

    /* ---------------------------------------------------------------------- */
    /* Anti-Clip Protection: Throttle Prioritization Algorithm               */
    /* If any motor duty exceeds 1000, subtract excess Delta across all       */
    /* motors equally to preserve roll/pitch stabilization authority.         */
    /* ---------------------------------------------------------------------- */
    float max_m = m1;
    if (m2 > max_m)
        max_m = m2;
    if (m3 > max_m)
        max_m = m3;
    if (m4 > max_m)
        max_m = m4;

    if (max_m > (float)MIXER_MAX_PWM) {
        float excess = max_m - (float)MIXER_MAX_PWM;
        m1 -= excess;
        m2 -= excess;
        m3 -= excess;
        m4 -= excess;
    }

    /* Clamp floor to idle spin speed */
    if (m1 < (float)MIXER_IDLE_PWM)
        m1 = (float)MIXER_IDLE_PWM;
    if (m2 < (float)MIXER_IDLE_PWM)
        m2 = (float)MIXER_IDLE_PWM;
    if (m3 < (float)MIXER_IDLE_PWM)
        m3 = (float)MIXER_IDLE_PWM;
    if (m4 < (float)MIXER_IDLE_PWM)
        m4 = (float)MIXER_IDLE_PWM;

    /* Final ceiling clamp */
    if (m1 > (float)MIXER_MAX_PWM)
        m1 = (float)MIXER_MAX_PWM;
    if (m2 > (float)MIXER_MAX_PWM)
        m2 = (float)MIXER_MAX_PWM;
    if (m3 > (float)MIXER_MAX_PWM)
        m3 = (float)MIXER_MAX_PWM;
    if (m4 > (float)MIXER_MAX_PWM)
        m4 = (float)MIXER_MAX_PWM;

    out_pwm->m1 = (uint16_t)m1;
    out_pwm->m2 = (uint16_t)m2;
    out_pwm->m3 = (uint16_t)m3;
    out_pwm->m4 = (uint16_t)m4;
}

void motor_mixer_apply(const motor_pwm_output_t *pwm) {
    if (!pwm)
        return;
    hal_motor_set_pwm(0, pwm->m1);
    hal_motor_set_pwm(1, pwm->m2);
    hal_motor_set_pwm(2, pwm->m3);
    hal_motor_set_pwm(3, pwm->m4);
}

void motor_mixer_emergency_stop(void) {
    hal_motor_set_pwm(0, 0);
    hal_motor_set_pwm(1, 0);
    hal_motor_set_pwm(2, 0);
    hal_motor_set_pwm(3, 0);
}
