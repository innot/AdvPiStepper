#  Copyright (c) 2020 Thomas Holland (thomas@innot.de)
#  All rights reserved.
#
#  This code is licensed under the MIT License.
#
#  Refer to the LICENSE file which is part of the AdvPiStepper distribution or
#  to https://opensource.org/licenses/MIT for a text of the license.
#
#

""" Stepper Driver"""

import time
import multiprocessing
from typing import Dict, Any, Union

# local imports
from .common import *
from .driver_base import DriverBase
from .stepper_process import StepperProcess, Verb, Noun, Command


class AdvPiStepper(object):
    """
    classdocs
    """

    def __init__(self, driver=None, parameters: Dict[str, Any] = None):
        """
        :param driver:
            The GPIO driver used to translate steps to pigpio pulses
            and waves. The stepper may contain some optional info
            about the actual stepper motor (max. speed etc.)
            Defaults to a debug stepper (no actual gpio).
        :type driver: DriverBase
        :param parameters:
            Optinal list of parameters to override default values.
        :type parameters: Dict[str,Any]
        """

        if driver is None:
            driver = DriverBase()

        # Get the default speed/accel/decel parameters from the driver
        params = driver.parameters
        if parameters is not None:
            # Use   r passed some parameters to extend or override the defaults.
            params.update(parameters)

        # setup and start the background process.
        c_pipe_remote, self.c_pipe = multiprocessing.Pipe()
        self.r_pipe, r_pipe_remote = multiprocessing.Pipe()
        self.run_lock = multiprocessing.Lock()

        self.process = StepperProcess(c_pipe_remote, r_pipe_remote, self.run_lock, driver, params)

        self.process.start()
        self.send_cmd(Verb.NOP, None)  # Wait for the Process to be ready
        self._wait_for_idle()

        self.parameters = params  # keep the current parameters for reference

    def __del__(self):
        if self.process.is_alive():
            # terminate the stepper process
            self.close()

    @property
    def current_position(self) -> int:
        """
        Get the current position of the motor.

        The position will be in steps or microsteps from the origin.

        While the motor is running the reported current position might lag the true current position
        by 1 or more steps due to the asynchrounous nature of AdvPiStepper.

        This property is read-only.

        :returns: the current motor position in steps / microsteps.
        :rtype: int
        """
        result = int(self._get_value(Noun.VAL_CURRENT_POSITION))
        return result

    @property
    def target_position(self) -> int:
        """
        Get the current target position of the driver.

        This is the position the stepper driver is currently moving to.

        This property is read-only.

        :return: the target position in steps / microsteps from origin.
        :rtype: int
        """
        result = int(self._get_value(Noun.VAL_TARGET_POSITION))
        return result

    @property
    def target_speed(self) -> float:
        """
        Get the selected target speed.

        During acceleration / deceleration
        the actual speed may be less than the target speed.

        :return: The speed in steps or microsteps per second
        :rtype: float
        """
        result = float(self._get_value(Noun.VAL_TARGET_SPEED))
        return result

    @target_speed.setter
    def target_speed(self, speed: float):
        """
        Set the target speed.

        This is the speed the controller will
        accelerate to and maintain once reached. The speed is
        independent from the direction, therefore the speed must be
        greater than 0.

        :param speed: target speed in steps/microsteps per second.
        :type speed: float
        :raises ValueError: When the given speed is 0 or less.
        """
        if speed <= 0.0:
            raise ValueError(f"Speed must be > 0.0, was {speed}")

        self.send_cmd(Verb.SPEED, speed)

    @property
    def current_speed(self) -> float:
        """
        Get the current speed.

        During acceleration / deceleration the current speed will be
        less than the target speed. Also during accel/decels and due
        to the asynchronous nature of AdvPiStepper the returned value
        might be a microseconds old and therefore not accurate.

        This property is read-only.

        :return: The speed in steps or microsteps per second
        :rtype: float
        """
        result = self._get_value(Noun.VAL_CURRENT_SPEED)
        return float(result)

    @property
    def acceleration(self) -> float:
        """
        Get the current acceleration rate.

        :return: The set acceleration in steps per second squared.
        :rtype: float
        """
        result = self._get_value(Noun.VAL_ACCELERATION)
        return float(result)

    @acceleration.setter
    def acceleration(self, rate: float):
        """
        Sets the desired acceleration in steps per second squared.

        High values may cause lost steps and stalled motors

        This property will override any default acceleration rate
        set by the driver. Any changes to this rate will be applied
        immediately and will affect any ongoing acceleration.

        :param rate: Must be greater than 0.
        :type rate: float
        :raises ValueError: if the rate is not valid.
        """
        if rate <= 0.0:
            raise ValueError(f"Acceleration must be greater than 0.0, was {rate}")

        self.send_cmd(Verb.ACCELERATION, rate)

    @property
    def deceleration(self):
        """
        Get the current deceleration rate.

        :return: The set deceleration in steps per second squared.
        :rtype: float
        """
        result = self._get_value(Noun.VAL_DECELERATION)
        return float(result)

    @deceleration.setter
    def deceleration(self, rate: float):
        """Sets the desired deceleration in steps per second squared.

        High values may cause lost steps due to motor inertia.

        This property will override any default deceleration rate
        set by the driver. Any changes to this rate will be applied
        immediately and will affect any ongoing deceleration.

        :param rate: Must be greater than 0.
        :type rate: float
        :raises ValueError: if the rate is not valid.
        """

        if rate <= 0.0:
            raise ValueError(f"Deceleration must be greater than 0.0, was {rate}")

        self.send_cmd(Verb.DECELARATION, rate)

    @property
    def full_steps_per_rev(self) -> int:
        """
        Get the number of full steps for a single revolution of the stepper motor.

        :returns: number of steps. 0 if not defined.
        :rtype: int
        """
        result = self._get_value(Noun.VAL_FULL_STEPS_PER_REV)
        return result

    @full_steps_per_rev.setter
    def full_steps_per_rev(self, steps: int):
        """
        Set the number of full steps for one complete revolution.

        Overrides any default value that may have been set by the driver.

        Is applied immediately and will effect any succeding
        move_deg() or moveto_deg() calls.

        :param steps: number of steps. May be 0 to indicate an undefined value.
        :type steps: int
        :raises ValueError: If the argument is not an integer 0 or greater.
        """
        if steps < 0:
            raise ValueError("steps must be 2 or greater")

        self.send_cmd(Verb.FULL_STEPS_PER_REV, steps)

    @property
    def microsteps(self) -> int:
        """
        Number of microsteps per full step.

        The number must be from the list of supported MICROSTEP_OPTIONS.
        Changing microsteps while the stepper motor is running may or may
        not work - depending on the driver. Refer to the driver documentation
        for changing microsteps while running.
        Some drivers need to sync their internal step sequencer before changing
        the microstep setting. Therefore the change may happen at some
        point in the future without any guarantee about the exact step.

        .. note::

            If the microstep setting is changed while the motor is running the
            absolute speed will be unchanged, i.e. the target speed (in steps per
            second) will be scaled by new_microsteps / old_microsteps.

        :type: int
        """
        result = self._get_value(Noun.VAL_MICROSTEPS)
        return result

    @microsteps.setter
    def microsteps(self, steps: int):
        """
        Set the number of microsteps per full step.

        :param steps: Requested number of microsteps per full step.
        :type steps: int
        :returns: position at which the change in microsteps has occured or will occure.
        :rtype: int
        :raises ValueError: if the requested microsteps are not supported by the driver.
        """
        if steps not in self.parameters[MICROSTEP_OPTIONS]:
            print(self.parameters)
            raise ValueError(
                f"Given microstep setting ({steps}) is not valid. Options are {self.parameters[MICROSTEP_OPTIONS]}")

        self.send_cmd(Verb.MICROSTEPS, steps)
        ready = self.r_pipe.poll(1.0)    # Should not time out - just in case
        if ready:
            retval = self.r_pipe.recv()
            print(f"microstep change returned:{retval}")
        else:
            raise EOFError("Microstep change timed out. Maybe backend down?")

    def move(self, steps: int, speed: float = None, block: bool = False):
        """
        Move the given number of steps relative to a position.

        If called while the motor is idle the move will be relative to the current
        position. If the motor is already executing a move the new move will be
        relative to the previous target position. If the motor is running in
        continuous mode the new move will be relative to the current position.

        :param steps:   Number of steps, full or microsteps.
                        Positiv for forward / clockwise,
                        negative for backwards / counterclockwise.
        :type steps: int
        :param speed:   Target speed in steps or microsteps per second.
                        Must be >0. Optional, default is the most recent target speed.
        :type speed: float
        :param block:   When 'True' waits for the move to complete.
                        Default 'False', i.e. call will return immediately.
        :type block:    bool
        :raises ValueError: if the speed is 0 or less.
                """
        if speed is None:
            speed = self.target_speed
        if speed <= 0:
            raise ValueError(f"Argument speed must be > 0.0, was {speed}")
        if not isinstance(steps, int):
            raise ValueError(f"Argument steps must be an integer, was {type(steps).__name__}")

        self.send_cmd(Verb.SPEED, speed)
        self.send_cmd(Verb.MOVE, steps)

        if block:
            self._wait_for_idle()

    def move_to(self, absolut):
        """
        Move to the given location.

        Use set_zero() to define the origin.
        This function blocks until all steps have been performed.
        """
        pass

    def run(self, direction: int, speed: float = 0.0):
        """
        Run the motor constantly.

        The motor will accelerate to and maintain a given speed. It will run
        until either stopped with stop() or overriden by any move() / move_to()
        call.
        This method can only be run as non-blocking for obvious reasons.

        :param direction: Direction of movement. Either CW (1) or CCW (-1).
        :type direction: int
        :param speed: Speed in steps per second. Optional, default is target_speed.
        :type speed: float
        :raises ValueError: if either the direction is not CW/CCW or if the speed
                            is 0 or less.
        """
        if speed == 0.0:
            speed = self.target_speed

        if direction != CW and direction != CCW:
            raise ValueError(f"Argument direction must be CW (1) or CCW (-1), was {direction}")
        if speed < 0.0:
            raise ValueError(f"Argument speed must be greater than 0.0, was {speed}")

        self.send_cmd(Verb.SPEED, speed)
        self.send_cmd(Verb.RUN, direction)

    def stop(self, block: bool = False):
        """
        Decelerate the motor to a complete stop.

        :param block:   When 'True' waits for the stop to complete.
                        Default 'False', i.e. call will return immediately.
        :type block:    bool
        """
        self.send_cmd(Verb.STOP)
        if block:
            self._wait_for_idle()

    def hardstop(self, block: bool = False):
        """
        Stops the motor immediately.

        How the motor is stopped depends on the motor driver. Usually
        the driver will just deenergize all motor coils.

        Due to inertia calling this on a moving motor will probably cause
        unaccounted motor steps. The current_position may not be accurate
        anymore and it is up to the caller to get the motor to a consistent
        state if so required.

        :param block:   When 'True' waits for the driver to initiate the hard stop.
                        Default 'False', i.e. call will return immediately.
        :type block:    bool
        """
        self.send_cmd(Verb.HARD_STOP)
        if block:
            self._wait_for_idle()

    def zero(self):
        """
        Reset the current position to 0.

        If called during a move the move will not be affected, i.e. it will continue
        for the given number of steps. But after it has finished the current position
        will be the number of steps performed since the call to zero().
        """
        self.send_cmd(Verb.ZERO)

    def engage(self, block: bool = False):
        """
        Energize the coils of the stepper motor.

        The coils are automatically engaged by any move / run command.
        This mehtod should not be called while the motor is already moving.

        :param block:   When 'True' waits for the driver to energize.
                        Default 'False', i.e. call will return immediately.
        :type block:    bool
        """
        self.send_cmd(Verb.ENGAGE)
        if block:
            self._wait_for_idle()

    def release(self, block: bool = False):
        """
        Deenergize the coils of the stepper motor.

        Deenergizing the coils will stop the motor from converting current
        into heat at the expense of yreduced holding torque.
        Also, when using microsteps the motor may (or may not) move to an
        adjacent full step.

        Calling this method while a move is underway is similar to a hard stop.

        :param block:   When 'True' waits for the driver to release.
                        Default 'False', i.e. call will return immediately.
        :type block:    bool

        """
        self.send_cmd(Verb.RELEASE)
        if block:
            self._wait_for_idle()

    def close(self):
        """
        End the stepper driver.

        All resources are released.
        This is called automatically when the AdvPiStepper object is garbage collected.
        """
        try:
            self.send_cmd(Verb.QUIT)
            time.sleep(0.1)
            self.c_pipe.close()
            self.r_pipe.close()
            self.process.join()
        except(EOFError, OSError, BrokenPipeError):
            # maybe the object is already closed.
            pass

    def send_cmd(self, verb: Verb, noun: Union[int, float, Noun] = None):
        """Send a command to the backend and wait until the backend has acknowledged.
        :param verb: The command to execute
        :type verb: Verb
        :param noun: An optional parameter
        :type noun: Noun
        :raises EOFError: when the backend does not acknowlege the command.
        """
        cmd = Command(verb, noun)
#        print(f"send command {cmd}")
        self.c_pipe.send(cmd)
        ack = self.c_pipe.poll(3.0)  # 3 seconds is rather long but required when accessing a remote Pi.
        if ack:
            retval = self.c_pipe.recv()
            print(f"retval for cmd {cmd}:{retval}")
        else:
            raise EOFError("Command not acknowledged after 3 second. Maybe backend down?")

    def _get_value(self, noun: Noun) -> Union[int, float, bool]:
        """Retrieve the given parameter from the stepper process.
        This method blocks until the value is returned by the process, but
        not longer than 1 second (responses time should be in the
        sub-microsecond range.

        :param noun: The parameter to fetch.
        :type noun: Noun.
        :return: The requested value.
        :rtype: object"""

        self.send_cmd(Verb.GET, noun)
        self.r_pipe.poll(1)  # if no result after 1 second then the other Process is stuck
        result = self.r_pipe.recv()
        if result.noun != noun:
            # todo do something with the unexpected result
            print(f"received unexpected result {result}")
        else:
            return result.value

    def _wait_for_idle(self):
        print(f"Waiting for idle @time {time.time()}")
        self.run_lock.acquire()
        self.run_lock.release()
        print(f"Idle received @time {time.time()}")
