#  Copyright (c) 2020 Thomas Holland (thomas@innot.de)
#  All rights reserved.
#
#  This code is licensed under the MIT License.
#
#  Refer to the LICENSE file which is part of the AdvPiStepper distribution or
#  to https://opensource.org/licenses/MIT for a text of the license.
#
#

"""
Definitions used by the AdvPiStepper

CW and CCW constants defining clockwise / couterclockwise motions.

The Keys which are used as parameters to describe a motor and the driver.

* MAX_SPEED:            Maximum speed in steps per second. This is not a limit, just a recommendation.
* MAX_TORQUE_SPEED:     Maximum speed at which the motor will still deliver full torque.
* ACCELERATION_RATE:    Acceleration in steps per second squared.
* DECELERATION_RATE:    Deceleration in steps per second squared.
* FULL_STEPS_PER_REV:   Number of full (not micro-)steps per one revolution.
* MICROSTEP_OPTIONS:    Tupel of all microsteps options.
* MICROSTEP_DEFAULT:    The prefered microstep rate of the driver.

Other parameters which can be passed to the AdvPiStepper class

* PIGPIO_ADDR:  The hostname of the system where the pigpio daemon is running on.
* PIGPIO_PORT:  The port on which the pigpio daemon is listening on.

"""
CW: int = 1
"""Clockwise/forward rotation. Just an internal designation. True
direction may depend on the wiring of the stepper motor."""

CCW: int = -1
"""Counterclockwise/backward rotation. Just an internal designation.
True direction may depend on the wiring of the stepper motor."""


# Parameter Keys

MAX_SPEED: str = "max_speed"
"""Maximum speed in steps per second. This is not a limit, just a recommendation"""

MAX_TORQUE_SPEED: str = "max_torque_speed"
"""Maximum speed at which the motor will still deliver full torque."""

ACCELERATION_RATE: str = "acceleration_rate"
"""Acceleration in steps per second squared."""

DECELERATION_RATE: str = "deceleration_rate"
"""Decelearation in steps per second squared."""

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
