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
Driver for generic Step & Direction Stepper Motor drivers.

Baseclass for all Step / Dir motor drivers, but can also be used by itself.
It sets the direction GPIO pin for the current direction and generates
step pulses on the step GPIO pin.

By default the direction is setting the directio pin to high for a clockwise turn
and low for a counterclockwise turn. This can be changed by the :const:`DIRECTION_INVERT`
parameter.

Unless overridden by a subclass or by the user this driver uses the following
default parameters:

- MAX_SPEED: 1000 steps/second
- MAX_TORQUE_SPEED: 100 steps/second
- ACCELERATION_RATE: 2000 steps / second^2
- DECELERATION_RATE: 3000 steps / second^2
- FULL_STEPS_PER_REV: 200 Full steps per revolution (1.8° per step)

- DIRECTION_CHANGE_DELAY: 10 µs
- STEP_PULSE_LENGTH: 10 µs
- STEP_PULSE_DELAY: 10 µs

Besides the (optional) parameters this driver needs the the 2 GPIO pins connected to
the step and direction inputs of the driver.

"""

import time

from .driver_base import *


class DriverStepDirGeneric(DriverBase):
    """
    Basic Step & Direction driver module.

    All pins use the pigpio/broadcom numbering scheme.

    :param step_pin: GPIO pin number for the step signal
    :type step_pin: int
    :param dir_pin: GPIO pin number for the direction signal
    :type dir_pin: int
    :param parameters: Optional parameters to override the default values.
    :type parameters: dict, optional

    """

    _step_dir_generic_defaults: Dict[str, Any] = {
        DRIVER_NAME: "Generic Step / Direction driver",
        MAX_SPEED: 1000.0,
        MAX_TORQUE_SPEED: 100.0,
        ACCELERATION_RATE: 2000,
        DECELERATION_RATE: 3000,
        FULL_STEPS_PER_REV: 400,

        # The timings are very conservative, however they are still 1-2 magnitudes shorter than
        # the shortest achivable pulse speed of AdvPiStepper.
        DIRECTION_CHANGE_DELAY: 10,
        STEP_PULSE_LENGTH: 10,
        STEP_PULSE_DELAY: 10,
    }

    def __init__(self, step_pin, dir_pin, parameters: Dict[str, Any] = None):

        p: Dict[str, Any] = self._step_dir_generic_defaults  # default values
        if parameters is not None:
            p.update(parameters)  # replace defaults with custom values

        super().__init__(p)

        self._gpio_step_pin = step_pin
        self._gpio_dir_pin = dir_pin

        # GPIO state
        self._engaged = False

        self._current_direction = CW
        self._invert_direction = int(p.get(DIRECTION_INVERT, False))
        self._pulse_length = self.parameters[STEP_PULSE_LENGTH]
        self._pulse_min_delay = self.parameters[STEP_PULSE_DELAY]

    @property
    def gpio_step_pin(self) -> int:
        """Pin number of the step output.

        This property can be written to, however changing the GPIO pin
        while the motor is running is propably not a good idea.

        :Type: int, 0 <= n <= 56
        """
        return self._gpio_step_pin

    @gpio_step_pin.setter
    def gpio_step_pin(self, pin: int):
        if not isinstance(pin, int) or pin < 0:
            raise ValueError(f"Invalid pin number {pin}")

        self._gpio_step_pin = pin

    def init(self, pi: pigpio.pi):
        """Initialize the driver.
        The base implementation configures the step and direction GPIOs
        for output.
        Subclasses may override this method to do further initializion as required
        by the motor driver.

        .. note::
            This method should only be called by the stepper process.

        :param pi: the pigpio instance to use.
        """
        super().init(pi)  # The parent class keeps the pigpio instance for us.

        pi.set_mode(self._gpio_step_pin, pigpio.OUTPUT)
        pi.write(self._gpio_step_pin, 0)

        pi.set_mode(self._gpio_dir_pin, pigpio.OUTPUT)
        pi.write(self._gpio_dir_pin, 0)

    def engage(self):
        """Energize the coils.
        The base implementation does not do anything. Subclasses may override this method
        to set an enable pin as required.
        """
        pass

    def release(self):
        """Deenergize all coils.
        The base implementation does not do anything. Subclasses may override this method
        to clear an enable pin as required.
        """
        pass

    def hard_stop(self):
        """Perform a hard stop where the motor is stop immediately, even
        at the expense of lost steps.
        By default the motor is just disengaged. Motor drivers with special hard stop
        functionality should override this method.
        """
        self.release()

    def set_microsteps(self, steps: int) -> bool:
        """
        Set the microsteps.

        This method will only be successful if the driver is ready for a change in
        microsteps, which can be checked with :meth:`steps_until_change_microsteps` method.

        .. note::
            The base implementation does not support microsteps. Subclasses supporting
            microsteps must override this method to implement the microstep setting
            logic.

        :param steps:
        :type steps: int
        :return: 'True' if the change was successfull, 'False' if the microsteps could not be changed.
        """
        return False

    def steps_until_change_microsteps(self, microsteps: int) -> int:
        """Checks when the the requested microstep setting can be changed.

        The result is in steps. If the result is 0 the driver is ready for a
        change in microsteps. Positive values are the number of steps which have
        to be performed before the change is possible (e.g. to sync to the next
        full step first). A negative return value means that the driver can not change
        to the new value, either because it is not supported or the change can only be
        made when the motor is not running.

        .. note::
            The base implementation does not support microsteps. Subclasses supporting
            microsteps must override this method to implement the microstep setting
            logic.

        :param microsteps: Requested microstep option, either FULLSTEP (1) or HALFSTEP (2)
        :type microsteps: int
        :returns: Either 0 (change possible right now) or n (change possibel after the n steps).
            Negative if microstep was neither 1 nor 2.
        :rtype: int
        """
        return -1

    @DriverBase.direction.setter
    def direction(self, direction: int):
        DriverBase.direction = direction
        if direction > 0:
            self._pi.write(self._gpio_dir_pin, 1)
        else:
            self._pi.write(self._gpio_dir_pin, 0)

        time.sleep(self.parameters[DIRECTION_CHANGE_DELAY] / 1000000)

    def perform_step(self, delay: int) -> list:
        """Generate a pigpio wave which
        * sets the step pin high
        * waits for STEP_PULSE_LENGTH microseconds
        * sets the step pin low
        * waits for (delay - STEP_PULSE_LENGTH) microseconds

        """

        # calculate the delay after the step. The minimum time after a step pulse is
        # taken into account, which could in theory affect the timing (wave longer than
        # given delay), but for reasonable delays (step delay in the microsecends, overall delay
        # in the hundreds of microseconds) this should not be a problem.
        delay_after_step = max(delay - self._pulse_length, self._pulse_min_delay)

        wave = [pigpio.pulse(1 << self._gpio_step_pin, 0, self._pulse_length),
                pigpio.pulse(0, 1 << self._gpio_step_pin, delay_after_step)]

        return wave
