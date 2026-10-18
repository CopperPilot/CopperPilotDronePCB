idf_component_register(
    SRCS
        "src/mpu6050.c"
        "src/ahrs.c"
        "src/pid.c"
        "src/motor_mixer.c"
    INCLUDE_DIRS "include"
    REQUIRES hal
)
