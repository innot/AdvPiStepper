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
Driver for the popular 28BYJ-48 stepper motor.

The 28BYJ-48 is a small, 5V or 12V stepper motor with an integrated reduction gear which
results in 2048 full steps per revolution of the output shaft. Due to the high
reduction gear (64:1), this stepper motor is rather slow.
Without any hacks (e.g. higher voltage; bipolar mods) and without much load
the 28BYJ-48 should be able to do about 15 rpm or about 500 steps per second.

The 28BYJ-48 is a unipolar motor and is often sold together with a small driver board
based on the ULN2003 Darlington array for less than 3€.

This driver just defines the following parameters for this motor, guessed from this
`datasheet <https://www.digikey.de/de/datasheets/mikroelektronika/mikroelektronika-step-motor-5v-28byj48-datasheet>`__
with the help of the `stepper motor glossary <https://www.anaheimautomation.com/support/stepper_motor_glossary.htm>`__

There are numerous variants of the 28BYJ-48 on the market with slightly different parameters, so
these parameters are on the conservative side. Each can be overriden by providing an optional
dictionary with alternative values to the constructor.

- MAX_SPEED: 650 steps/second (~10 rpm)
- MAX_TORQUE_SPEED: 120 steps/second
- ACCELERATION_RATE: 2000 steps / second^2
- DECELERATION_RATE: 4000 steps / second^2
- FULL_STEPS_PER_REV: 2048 Full steps per revolution
- MICROSTEP_OPTIONS: FULLSTEP or HALFSTEP.
- MICROSTEP_DEFAULT: HALFSTEP

Halfstep is the recommended rate for the 28BYJ-48

Besides the motor characteristics this driver uses colors for the 4 control wires which seem
to be standard for all 28BYJ-48 variants.

- pink / orange for A+ and A-
- yellow / blue for B+ and B-

.. note::
    The motor wires should not be connected to the Raspberry directly. To provide sufficient
    power to the motor a driver like the `ULN2003A <https://en.wikipedia.org/wiki/ULN20030>`__
    should be used.
"""

from advpistepper.driver_unipolar_generic import *


class Driver28BYJ48(UnipolarDriver):
    """
    :param pink: GPIO pin the pink wire (A+)is connect to (Broadcom / pigpio numbering)
    :type pink: int
    :param orange: GPIO pin the orange wire (A-) is connect to (Broadcom / pigpio numbering)
    :type orange: int
    :param yellow: GPIO pin the yellow wire (B+) is connect to (Broadcom / pigpio numbering)
    :type yellow: int
    :param blue: GPIO pin the blue wire (B-) is connect to (Broadcom / pigpio numbering)
    :type blue: int
    :param parameters: Optional parameters to override the default values.
    :type parameters: dict, optional
    """

    _28byj48_defaults: Dict[str, Any] = {
        DRIVER_NAME: "28BYJ-48",
        MAX_SPEED: 650.0,
        MAX_TORQUE_SPEED: 120.0,
        ACCELERATION_RATE: 2000,
        # TBD: for now an arbitrary number to accelerate to full speed in approx. 1/4 second
        DECELERATION_RATE: 3000,
        # TBD: somewhat higher than acceleration deu to the internal friction helping with the deceleration
        FULL_STEPS_PER_REV: 2048,
        MICROSTEP_DEFAULT: HALFSTEP
    }

    def __init__(self, pink, orange, yellow, blue, parameters: Dict[str, Any] = None):

        p: Dict[str, Any] = self._28byj48_defaults  # default values
        if parameters is not None:
            p.update(parameters)  # replace defaults with custom values

        super().__init__(pink, orange, yellow, blue, parameters=p)
