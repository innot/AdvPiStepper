#  Copyright (c) 2020 Thomas Holland (thomas@innot.de)
#  All rights reserved.
#
#  This code is licensed under the MIT License.
#
#  Refer to the LICENSE file which is part of the AdvPiStepper distribution or
#  to https://opensource.org/licenses/MIT for a text of the license.
#
#

"""The :class:`AdvPiStepper` class is the main interface"""

import time
import multiprocessing
import logging
from typing import Dict, Any, Union

# local imports
from advpistepper.common import MICROSTEP_OPTIONS, CW, CCW
from advpistepper.driver_base import DriverBase
from advpistepper.stepper_process import StepperProcess, Verb, Noun, Command


class AdvPiStepper(object):
    """
    :param driver:
        The GPIO driver used to translate steps to pigpio pulses
        and waves. The stepper may contain some optional info
        about the actual stepper motor (max. speed etc.).
        Defaults to a dummy driver (no actual gpio).
    :type driver: DriverBase
    :param parameters:
        Optinal list of parameters to override default values.
        Refer to `parameters` for more details
    :type parameters: Dict[str,Any]
    """

    def __init__(self, driver=None, parameters: Dict[str, Any] = None):

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
        self._send_cmd(Verb.NOP, None)  # Wait for the Process to be ready
        self._wait_for_idle()

        self.parameters = params  # keep the current parameters for reference

    def __del__(self):
        if self.process.is_alive():
            # terminate the stepper process
            self.close()

    @property
    def current_position(self) -> int:
        """
        The current position of the motor.

        The position will be in steps or microsteps from the origin.

        While the motor is running the reported current position might lag the true current position
        by 1 or more steps due to the asynchrounous nature of AdvPiStepper.

        This property is read-only.

        :type: int
        """
        result = int(self._get_value(Noun.VAL_CURRENT_POSITION))
        return result

    @property
    def target_position(self) -> int:
        """
        The current target position of the driver.

        This is the position the stepper driver is currently moving to.

        This property is read-only.

        :type: int
        """
        result = int(self._get_value(Noun.VAL_TARGET_POSITION))
        return result

    @property
    def target_speed(self) -> float:
        """
        The selected target speed in steps or microsteps per second.

        This is the speed the stepper will accelerate to and maintain during moves.
        It is independant of the direction and must be greater than 0.
        Setting a target speed of 0 or less will cause a `ValueError` exception.

        .. note::
            High values (>1.000 sps) may cause timing jitter and even lost steps.

        :type: float
        """
        result = float(self._get_value(Noun.VAL_TARGET_SPEED))
        return result

    @target_speed.setter
    def target_speed(self, speed: float):
        if speed <= 0.0:
            raise ValueError(f"Speed must be > 0.0, was {speed}")

        self._send_cmd(Verb.SPEED, speed)

    @property
    def current_speed(self) -> float:
        """
        The current speed in steps or microsteps per second.

        During acceleration / deceleration the current speed will be
        less than the target speed. Due to the asynchronous nature of
        AdvPiStepper the returned value might lag the actual speed.

        This property is read-only.

        :type: float
        """
        result = self._get_value(Noun.VAL_CURRENT_SPEED)
        return float(result)

    @property
    def acceleration(self) -> float:
        """
        The current acceleration rate in steps or microsteps per second :sup:`2`

        This property will override any default acceleration rate
        set by the driver. Any changes to this rate will be applied
        immediately and will affect any ongoing acceleration.

        .. note::
            High values may cause lost steps and motor stalls.

        The value must be greater than zero. Trying to set a value of 0 or less will
        cause a `ValueError` exception.

        :type: float
        """
        result = self._get_value(Noun.VAL_ACCELERATION)
        return float(result)

    @acceleration.setter
    def acceleration(self, rate: float):
        if rate <= 0.0:
            raise ValueError(f"Acceleration must be greater than 0.0, was {rate}")

        self._send_cmd(Verb.ACCELERATION, rate)

    @property
    def deceleration(self):
        """
        The current deceleration rate in steps or microsteps per second :sup:`2`

        This property will override any default deceleration rate
        set by the driver. Any changes to this rate will be applied
        immediately and will affect any ongoing deceleration.

        .. note::
            High values may cause unaccounted steps due to motor inertia.

        The value must be greater than zero. Trying to set a value of 0 or less will
        cause a `ValueError` exception.

        :type: float
        """
        result = self._get_value(Noun.VAL_DECELERATION)
        return float(result)

    @deceleration.setter
    def deceleration(self, rate: float):
        if rate <= 0.0:
            raise ValueError(f"Deceleration must be greater than 0.0, was {rate}")

        self._send_cmd(Verb.DECELARATION, rate)

    @property
    def full_steps_per_rev(self) -> int:
        """
        The number of full steps for one complete revolution of the motor.

        Overrides any default value that may have been set by the driver.

        Is applied immediately and will effect any succeding
        move_deg() or moveto_deg() calls.

        The value must be 2 or greater. Trying to set a value less of 1 or less will
        cause a `ValueError` exception.

        :type: int
        """
        result = self._get_value(Noun.VAL_FULL_STEPS_PER_REV)
        return result

    @full_steps_per_rev.setter
    def full_steps_per_rev(self, steps: int):
        if steps < 0:
            raise ValueError("steps must be 2 or greater")

        self._send_cmd(Verb.FULL_STEPS_PER_REV, steps)

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

        Trying to set a value that is not supported by the driver will cause a
        `ValueError` exception.

        :type: int
        """
        result = self._get_value(Noun.VAL_MICROSTEPS)
        return result

    @microsteps.setter
    def microsteps(self, steps: int):
        if steps not in self.parameters[MICROSTEP_OPTIONS]:
            raise ValueError(
                f"Given microstep setting ({steps}) is not valid. Options are {self.parameters[MICROSTEP_OPTIONS]}")

        self._send_cmd(Verb.MICROSTEPS, steps)
        ready = self.r_pipe.poll(1.0)    # Should not time out - just in case
        if ready:
            retval = self.r_pipe.recv()
            # todo do something with the returned value, which is the position at which the step change
            # will occur.

        else:
            raise EOFError("Microstep change timed out. Maybe backend down?")

    @property
    def is_running(self) -> bool:
        """
        Flag to indicate that the the stepper is still running.

        :return: True if the stepper engine is not idle.
        """
        idle = self.run_lock.acquire(block=False)  # can only be acquired when released by the backend (i.e. not busy)
        if idle:
            self.run_lock.release()  # release immediatly so that the backend can acquire it again.

        return not idle

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
        :param block:   When `True` waits for the move to complete.
                        Default `False`, i.e. call will return immediately.
        :type block:    bool
        :raises ValueError: if the speed is 0 or less.
                """
        if not isinstance(steps, int):
            raise ValueError(f"Argument steps must be an integer, was {type(steps).__name__}")

        if speed is not None:
            if speed <= 0.0:
                raise ValueError(f"Argument speed must be > 0.0, was {speed}")
            self._send_cmd(Verb.SPEED, speed)

        self._send_cmd(Verb.MOVE, steps)

        if block:
            self._wait_for_idle()

    def move_to(self, position: int, speed: float=None, block: bool=False):
        """
        Move to the given absolute location.

        Location is in steps or microsteps from the origin, which is the position set by :meth:`zero`
        (or the position at initialization) and can be negative.
        This can be called while a move is underway.

        :param position:    Target position in steps or microsteps.
        :type position: int
        :param speed:   Target speed in steps or microsteps per second.
                        Must be >0. Optional, default is the most recent target speed.
        :type speed: float
        :param block:   When `True` waits for the move to complete.
                        Default `False`, i.e. call will return immediately.
        :type block:    bool
        :raises ValueError: if the speed is 0 or less.
        """
        if not isinstance(position, int):
            raise ValueError(f"Argument position must be an integer, was {type(position).__name__}")

        if speed is not None:
            if speed <= 0.0:
                raise ValueError(f"Argument speed must be > 0.0, was {speed}")
            self._send_cmd(Verb.SPEED, speed)

        self._send_cmd(Verb.MOVETO, position)

        if block:
            self._wait_for_idle()

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

        self._send_cmd(Verb.SPEED, speed)
        self._send_cmd(Verb.RUN, direction)

    def stop(self, block: bool = False):
        """
        Decelerate the motor to a complete stop.

        :param block:   When `True` waits for the stop to complete.
                        Default `False`, i.e. call will return immediately.
        :type block:    bool
        """
        self._send_cmd(Verb.STOP)
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

        :param block:   When `True` waits for the driver to initiate the hard stop.
                        Default `False`, i.e. call will return immediately.
        :type block:    bool
        """
        self._send_cmd(Verb.HARD_STOP)
        if block:
            self._wait_for_idle()

    def wait(self, timeout: float = None) -> bool:
        """
        Wait for the current move to finish.

        When invoked with a positive, floating-point value for timeout, block for at most the
        number of seconds specified by timeout.

        .. warning::
            If called without a timeout value while a :meth:`run` is running this method will
            not return.

        :param timeout: timeout in seconds
        :return: `True` is the move has finished, `False` if the wait timed out.
        """
        idle = self.run_lock.acquire(timeout=timeout)  # wait for the backend to realease the run lock
        if idle:
            self.run_lock.release()  # release immediatly so that the backend can acquire it again.

        return idle

    def zero(self):
        """
        Reset the current position to 0.

        If called during a move the move will not be affected, i.e. it will continue
        for the given number of steps. But after it has finished the current position
        will be the number of steps performed since the call to zero().
        """
        self._send_cmd(Verb.ZERO)

    def engage(self, block: bool = False):
        """
        Energize the coils of the stepper motor.

        The coils are automatically engaged by any move / run command.
        This method should not be called while the motor is already moving.

        :param block:   When `True` waits for the driver to energize.
                        Default `False`, i.e. call will return immediately.
        :type block:    bool
        """
        self._send_cmd(Verb.ENGAGE)
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

        :param block:   When `True` waits for the driver to release.
                        Default `False`, i.e. call will return immediately.
        :type block:    bool

        """
        self._send_cmd(Verb.RELEASE)
        if block:
            self._wait_for_idle()

    def close(self):
        """
        End the stepper driver.

        All resources are released.
        This is called automatically when the AdvPiStepper object is garbage collected.
        """
        try:
            self._send_cmd(Verb.QUIT)
            time.sleep(0.1)
            self.c_pipe.close()
            self.r_pipe.close()
            self.process.join()
        except(EOFError, OSError, BrokenPipeError):
            # maybe the object is already closed.
            pass

    def _send_cmd(self, verb: Verb, noun: Union[int, float, Noun] = None):
        """Send a command to the backend and wait until the backend has acknowledged.

        :param verb: The command to execute
        :type verb: Verb
        :param noun: An optional parameter
        :type noun: Noun
        :raises EOFError: when the backend does not acknowlege the command.
        """
        cmd = Command(verb, noun)
        logging.debug(f"Frontend: send command {cmd}")
        self.c_pipe.send(cmd)
        ack = self.c_pipe.poll(3.0)  # 3 seconds is rather long but required when accessing a remote Pi.
        if ack:
            retval = self.c_pipe.recv()
            logging.debug(f"Frontend: cmd {cmd} acknowledged")
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
        :rtype: object
        """

        self._send_cmd(Verb.GET, noun)
        self.r_pipe.poll(1)  # if no result after 1 second then the other Process is stuck
        result = self.r_pipe.recv()
        if result.noun != noun:
            # todo do something with the unexpected result
            logging.error(f"received unexpected result {result}")
        else:
            return result.value

    def _wait_for_idle(self):
        logging.debug(f"Frontend: Waiting for idle @time {time.time()}")
        self.run_lock.acquire()  # can only be acquired when released by the backend (i.e. not busy)
        self.run_lock.release()  # release immediatly so that the backend can acquire it again.
        logging.debug(f"Frontend: Idle received @time {time.time()}")
