"""
Created on 02.07.2020

@author: thoma
"""

CW: int = 1
"""Clockwise/forward rotation. Just an internal designation. True
direction may depend on the wiring of the stepper motor."""

CCW: int = -1
"""Counterclockwise/backward rotation. Just an internal designation.
True direction may depend on the wiring of the stepper motor."""

# Parameter Keys

MAX_SPEED: str = "max_speed"
"""Maximum speed in steps per second."""

MAX_TORQUE_SPEED: str = "max_torque_speed"
"""Maximum speed at which the motor will still deliver full torque."""

ACCELERATION_RATE: str = "acceleration_rate"
"""Acceleration in steps per second per second."""

DECELERATION_RATE: str = "deceleration_rate"
"""Decelearation in steps per second per second."""

FULL_STEPS_PER_REV: str = "full_steps_per_rev"
"""Number of full (not micro-)steps per one revolution."""

MICROSTEP_OPTIONS: str = "microstep_options"
"""Tupel of all microsteps options. Default is only full steps."""

MICROSTEP_DEFAULT = "microstep_default"
"""The prefered microstep rate of the driver."""

PIGPIO_ADDR = "pigpio_addr"
"""The hostname of the system where the pigpio daemon is running on. Default is empty for the localhost."""

PIGPIO_PORT = "pigpio_port"
"""The port on which the pigpio daemon is listening on. Default is empty to use the default pigpio port (8888)."""
