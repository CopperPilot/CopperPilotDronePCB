/**
 * @file pid.c
 * @brief Discrete PID controller implementation.
 */

#include "pid.h"

#include <math.h>

void pid_init(pid_controller_t *pid, float kp, float ki, float kd, float i_max, float out_max,
              float d_filter_hz) {
    if (!pid)
        return;

    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->i_max = fabsf(i_max);
    pid->out_max = fabsf(out_max);
    pid->d_filter_hz = (d_filter_hz > 0.0f) ? d_filter_hz : 30.0f;
    pid_reset(pid);
}

void pid_reset(pid_controller_t *pid) {
    if (!pid)
        return;
    pid->integrator = 0.0f;
    pid->prev_error = 0.0f;
    pid->d_lpf_state = 0.0f;
    pid->has_prev = false;
}

float pid_update(pid_controller_t *pid, float setpoint, float measurement, float dt_s) {
    if (!pid || dt_s <= 0.0f)
        return 0.0f;

    float error = setpoint - measurement;

    /* 1. Proportional term */
    float p_term = pid->kp * error;

    /* 2. Integral term with anti-windup clamping */
    pid->integrator += error * dt_s;
    if (pid->i_max > 0.0f) {
        if (pid->integrator > pid->i_max)
            pid->integrator = pid->i_max;
        else if (pid->integrator < -pid->i_max)
            pid->integrator = -pid->i_max;
    }
    float i_term = pid->ki * pid->integrator;

    /* 3. Derivative term with 1st-order low-pass filter */
    float d_term = 0.0f;
    if (pid->has_prev) {
        float raw_derivative = (error - pid->prev_error) / dt_s;

        /* Filter alpha = dt / (RC + dt), where RC = 1 / (2 * pi * f_cutoff) */
        float rc = 1.0f / (2.0f * 3.14159265f * pid->d_filter_hz);
        float alpha = dt_s / (rc + dt_s);
        pid->d_lpf_state += alpha * (raw_derivative - pid->d_lpf_state);

        d_term = pid->kd * pid->d_lpf_state;
    } else {
        pid->has_prev = true;
    }
    pid->prev_error = error;

    /* Combine terms and clamp */
    float output = p_term + i_term + d_term;
    if (pid->out_max > 0.0f) {
        if (output > pid->out_max)
            output = pid->out_max;
        else if (output < -pid->out_max)
            output = -pid->out_max;
    }

    return output;
}

void cascaded_axis_init(cascaded_axis_controller_t *axis, float angle_kp, float angle_ki,
                        float angle_out_max, float rate_kp, float rate_ki, float rate_kd,
                        float rate_i_max, float rate_out_max) {
    if (!axis)
        return;
    /* Outer angle loop has no derivative term */
    pid_init(&axis->angle_pid, angle_kp, angle_ki, 0.0f, angle_out_max * 0.5f, angle_out_max,
             30.0f);
    /* Inner rate loop handles high-frequency disturbances */
    pid_init(&axis->rate_pid, rate_kp, rate_ki, rate_kd, rate_i_max, rate_out_max, 30.0f);
}

void cascaded_axis_reset(cascaded_axis_controller_t *axis) {
    if (!axis)
        return;
    pid_reset(&axis->angle_pid);
    pid_reset(&axis->rate_pid);
}

float cascaded_axis_update(cascaded_axis_controller_t *axis, float target_angle_deg,
                           float measured_angle_deg, float measured_rate_dps, float dt_s) {
    if (!axis)
        return 0.0f;

    /* 1. Outer Loop: Attitude Error -> Target Angular Rate */
    float target_rate_dps =
        pid_update(&axis->angle_pid, target_angle_deg, measured_angle_deg, dt_s);

    /* 2. Inner Loop: Rate Error -> Motor Torque Output */
    return pid_update(&axis->rate_pid, target_rate_dps, measured_rate_dps, dt_s);
}
