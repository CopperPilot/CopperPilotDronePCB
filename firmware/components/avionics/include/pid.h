/**
 * @file pid.h
 * @brief Cascaded angle/rate PID controller with derivative filtering and anti-windup.
 */

#ifndef COPPERPILOT_PID_H
#define COPPERPILOT_PID_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    /* Tuning gains */
    float kp;
    float ki;
    float kd;

    /* Limits */
    float i_max;   /* Maximum integral authority */
    float out_max; /* Maximum controller output */

    /* Derivative filter */
    float d_filter_hz; /* Low-pass cutoff frequency in Hz */
    float d_lpf_state; /* Filter memory */

    /* Runtime state */
    float integrator;
    float prev_error;
    bool has_prev;
} pid_controller_t;

typedef struct {
    pid_controller_t angle_pid; /* Outer loop: Angle (deg) -> Rate (deg/s) */
    pid_controller_t rate_pid;  /* Inner loop: Rate (deg/s) -> Torque Command */
} cascaded_axis_controller_t;

void pid_init(pid_controller_t *pid, float kp, float ki, float kd, float i_max, float out_max,
              float d_filter_hz);
void pid_reset(pid_controller_t *pid);
float pid_update(pid_controller_t *pid, float setpoint, float measurement, float dt_s);

/* Cascaded dual-loop helper */
void cascaded_axis_init(cascaded_axis_controller_t *axis, float angle_kp, float angle_ki,
                        float angle_out_max, float rate_kp, float rate_ki, float rate_kd,
                        float rate_i_max, float rate_out_max);
void cascaded_axis_reset(cascaded_axis_controller_t *axis);
float cascaded_axis_update(cascaded_axis_controller_t *axis, float target_angle_deg,
                           float measured_angle_deg, float measured_rate_dps, float dt_s);

#ifdef __cplusplus
}
#endif

#endif /* COPPERPILOT_PID_H */
