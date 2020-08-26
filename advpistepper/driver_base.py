#  Copyright (c) 2020 Thomas Holland (thomas@innot.de)
#  All rights reserved.
#
#  This code is licensed under the MIT License.
#
#  Refer to the LICENSE file which is part of the AdvPiStepper distribution or
#  to https://opensource.org/licenses/MIT for a text of the license.
#
#


from typing import Dict, Any, Tuple

import pigpio

from advpistepper.common import *


class DriverBase(object):
    """The base class for all stepper drivers.
    This class should be subclassed for specfic drivers.

    At a minimum a driver should override :meth:`perform_step`
    to generate the gpio pulses. All other methods can be overridden as required.
    """

    db_defaults: Dict[str, Any] = {
        MAX_SPEED: 1000.0,
        MAX_TORQUE_SPEED: 100.0,
        ACCELERATION_RATE: 1000,
        DECELERATION_RATE: 1000,
        FULL_STEPS_PER_REV: 400,
        MICROSTEP_OPTIONS: (1,),
        MICROSTEP_DEFAULT: 1
    }

    def __init__(self, parameters: Dict[str, Any] = None):
        self._parameters: Dict[str, Any] = self.db_defaults  # default values
        if parameters is not None:
            self._parameters.update(parameters)  # replace defaults with custom values

        self._direction: int = CW
        """Direction of movement, either CW (1), CCW (-1)."""

        self._initialized: bool = False
        """Flag to indicate that the driver has been initialized and the
        GPIO pins have been set up."""

        self.engaged = False
        """Falg to indicate that the driver is engaged, i.e. current is supplied to the coils."""

        self._pi = None
        """pigpio handle. This value is set when the init() method is called from the
        stepper controller with a pigpio reference."""

        self._microsteps = self.parameters[MICROSTEP_DEFAULT]

    @property
    def parameters(self) -> Dict[str, Any]:
        """returns the physical parameters of the associated hardware
        (driver and motor). See common.py for the list of parameters
        :return: Dictionary with a copy of all parameters.
        :rtype: Dict[str, Any]
        """
        return self._parameters.copy()

    @parameters.setter
    def parameters(self, values: Dict[str, Any]):
        """Set one or more parameter.
        This will overwrite any previously set parameters with the same name.
        See common.py for a list of valid parameter names.
        :param values:  Dictionary with the new parameters.
                        Parameters with invalid names will be ignored.#
        :type values: Dict[str, Any]
        """
        self._parameters.update(values)

    @property
    def max_speed(self) -> float:
        """Returns the maximum recommended speed in steps per second.
        :returns: max speed
        :rtype: int
        """
        return self.parameters[MAX_SPEED]

    @max_speed.setter
    def max_speed(self, speed: float):
        """Set the maximum speed in steps per second.
        
        This is the number of steps per second maintained after the
        acceleration phase. 
        Higher values will reduce the motor torque and may cause lost
        steps and motor stalling.
        Subclasses should 
        
        :param speed: Maximum speed. Must be greater than 0.
                      Values below 1.0 are possible for very slow moves.
        :type speed: float
        """
        if speed <= 0:
            raise ValueError(f"MaxSpeed must be greater than 0, was {speed}")

        self.parameters[MAX_SPEED] = speed

    @property
    def microstep_options(self) -> Tuple[int]:
        """Return a tuple with all microstep options.
        :returns: tuple with int microstep options, e.g. (1,2,4,8)
        :rtype: Tuple[int]
        """
        return self.parameters[MICROSTEP_OPTIONS]

    @microstep_options.setter
    def microstep_options(self, options: Tuple[int]):
        """
        Tell the class which microstep options are available.
        :param options: tuple of available microstep value,
                        e.g. (1,2,4,8) for full- up to 1/8th step.
        :type options: Tuple[int]
        :raises ValueError: if the list is empty or has non-int entries.
        """

        if not options:  # empty tuple
            raise ValueError("Microstep options tuple must not be empty")

        for entry in options:
            if not isinstance(entry, int) or entry < 0:
                raise ValueError(f"Microstep options must be positive \
                                    integers, found {entry} in {options}")

        self.parameters[MICROSTEP_OPTIONS] = options

    def init(self, pi: pigpio.pi):
        """Initializes the driver, setting up the required GPIO pins.
        :param pi: the pigpio instance to use.
        """
        self._pi = pi
        self._initialized = True

    def engage(self):
        """Energize the coils."""
        self.engaged = True

    def release(self):
        """Deenergize all coils."""
        self.engaged = False

    @property
    def direction(self) -> int:
        """The current direction of the motor.
        Can be either clockwise (CW / 1) or counterclockwise (CCW / -1).
        When changed all subsequent calls to perform_step() will go in
        the given direction.
        It is up to the caller to ensure that the motor is able to change
        the direction of rotation, i.e. has come to a complete stop.
        """
        return self._direction

    @direction.setter
    def direction(self, direction: int):
        self._direction = direction

    @property
    def microsteps(self) -> int:
        """The currently set number of microsteps.
        This method will only be successful if the driver is ready for a change in
        microsteps, which can be checked with :meth:`steps_until_change_microsteps` method.
        """
        return self._microsteps

    @microsteps.setter
    def microsteps(self, steps: int) -> bool:
        self._microsteps = steps  # should be overridden by subclasses
        return True

    def steps_until_change_microsteps(self, microsteps: int) -> int:
        """Checks when the the requested microstep setting can be changed.
        The result is in steps. If the result is 0 the driver is ready for a
        change in microsteps. Positive values are the number of steps which have
        to be performed before the change is possible (e.g. to sync to the next
        full step first). A negative return value means that the driver can not change
        to the new value, either because it is not supported or the change can only be
        made when the motor is not running.

        :returns:   number of steps before microsteps value can be changed.
            0 if change is possible right now.
            negative if the requested microsteps can not be set at the moment.
        :rtype: int
        """
        return 0  # should be overriden in the subclasses.

    def perform_step(self, delay: int) -> list:
        """Returns a list of pigpio pulse objects (a wave) for a single
        step lasting delay microseconds.
        :param delay: total time for the step.
        :return: a pigpio wave (list of pulses)
        """
        # This default implementation does not perform any actual GPIO.
        # the returned list contains just a single delay pulse.
        # This can be used for timing tests and debugging.
        return [pigpio.pulse(0, 0, delay)]

    def hard_stop(self):
        """Perform a hard stop where the motor is stop immediately, even
        at the expense of lost steps.
        The default is just to de-energize the coils, but some more
        advanced stepper drivers may have braking or other means to come
        to a quick stop.
        Due to the asynchronous nature of the engine there might be
        multiple stepper motor pulses already in the pipeline that will
        be transmitted even after a call to hard_stop().
        Subclasses should take care that these pulses do not cause any
        further motor movement, e.g. by deactivtiong any GPIO output.
        """
        self.release()
