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
import pigpio

from dataclasses import dataclass
from enum import Enum, auto
from math import sqrt
from typing import Dict, Any, Union

from .common import *
from .driver_base import DriverBase

# All states of the stepper
IDLE = 0
"""Stepper is not running and the coils are deenergized."""

STOP = 1
"""Stepper is not running but the coils are energized
to hold the last position."""

ACCEL = 2
"""Stepper is accelerating to the target speed."""

INC = 3
"""After being in the RUN state the stepper is accelerating to
a new target speed."""

RUN = 4
"""Stepper is running at the given target speed."""

DEC = 5
"""Stepper is decelerating to a new, slower target speed."""

DECEL = 6
"""Stepper is decelerating to a STOP."""


@dataclass
class ControllerData:
    """
    Object containing all data for the speed controller.
    """

    state: int = IDLE
    """Current state of the stepper."""

    current_direction: int = 0
    """0 = at rest, CW = forward, CCW = backward."""

    c_n: int = 0
    """time from the current step to the next (in microseconds)."""

    c_min: int = 1000
    """Minimum time between steps (at max rate) in microseconds.

    This determines the maximum speed of the motor.
    Default is 1ms (1000steps per second), but the motor stepper driver
    should supply a more appropriate value for the connected motor and
    its GPIO stepper.
    """

    c_0: int = 10000
    """Initial time between steps at the start of a move
    (in microseconds). 10000 is just a placeholder. The actual value
    is calculated from the set acceleration.
    """

    c_target: int = 2000
    """Time between steps for the target speed (as set by speed())
    (in microseconds).
    """

    delay: int = 0
    """int: delay until the next step in microseconds."""

    target_speed: float = 100
    """Target speed in steps per second. Default is 100 steps per second."""

    speed: float = 0.0
    """Current speed in steps per second."""

    step: int = 0
    """The current step in the acceleration and deceleration phases."""

    decel_steps: int = 0
    """Number of steps required to decelerate to a full stop."""


class Verb(Enum):
    """List of Commands that can be send to the stepper background process."""
    # set target values
    SPEED = auto()
    ACCELERATION = auto()
    DECELERATION = auto()
    FULL_STEPS_PER_REV = auto()
    MICROSTEPS = auto()

    # Relative Moves
    MOVE = auto()
    MOVE_DEG = auto()
    MOVE_RAD = auto()

    # Absolute Moves
    MOVETO = auto()
    MOVETO_DEG = auto()
    MOVETO_RAD = auto()

    # Constant speed mode
    RUN = auto()
    STOP = auto()

    # reset absolut position
    ZERO = auto()

    # emergency stop
    HARD_STOP = auto()

    # end process
    QUIT = auto()

    # Coil control
    ENGAGE = auto()
    RELEASE = auto()

    # get value. The Noun contains the ID of the value. The value is returned via the results Pipe.
    GET = auto()

    # Do nothing operator. Used for setting up the Pipe
    NOP = auto()

    # Acknowledge the command
    ACKNOWLEDGE = auto()


class Noun(Enum):
    """List of values that can be queried with the GET Verb."""
    VAL_CURRENT_SPEED = auto()
    VAL_TARGET_SPEED = auto()
    VAL_CURRENT_POSITION = auto()
    VAL_TARGET_POSITION = auto()
    VAL_ACCELERATION = auto()
    VAL_DECELERATION = auto()
    VAL_FULL_STEPS_PER_REV = auto()
    VAL_MICROSTEPS = auto()
    VAL_ACKNOWLEDGE = auto()

    # Microstep return values
    MICROSTEP_NOT_POSSIBLE = auto()
    MICROSTEP_CHANGE_AT = auto()


@dataclass
class Command(object):
    """Command object passed from the frontend to the background Process."""
    verb: Verb = None
    noun: Union[Noun, int, float] = None

    def __init__(self, verb: Verb, noun: Union[Noun, int, float] = None):
        self.verb = verb
        self.noun = noun


@dataclass
class Result(object):
    """Result object passed from the background Process to the frontend."""
    noun: Noun = None
    value: Union[int, float, bool] = None

    def __init__(self, noun: Noun, value: Union[int, float, bool]):
        self.noun = noun
        self.value = value


@dataclass
class Statistics(object):
    number_of_steps: int = 0
    runtime: int = 0


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
        Get the currently set number of microsteps per full step.

        :returns: number betwenn 1 and the max supported number of microsteps.
        :rtype: int"""

        result = self._get_value(Noun.VAL_MICROSTEPS)
        return result

    @microsteps.setter
    def microsteps(self, steps: int):
        """
        Set the number of microsteps per full step.
        The number must be from the list of supported MICROSTEP_OPTIONS.
        Changing microsteps while the stepper motor is running may or may
        not work - depending on the driver. Refer to the driver documentation
        for changing microsteps while running.
        Some drivers need to sync their internal step sequencer before changing
        the microstep setting. Therefore the change may happen at some
        point in the future without any guarantee about the exact step.

        If the microstep setting is changed while the motor is running the
        absolute speed will be unchanged, i.e. the target speed (in steps per
        second) will be scaled by new_microsteps / old_microsteps.

        :param steps: 
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


class StepperProcess(multiprocessing.Process):

    def __init__(self, command_pipe: multiprocessing.Pipe, results_pipe: multiprocessing.Pipe,
                 run_lock,
                 driver: DriverBase = None,  parameters: Dict[str, Any] = None):
        super(StepperProcess, self).__init__()

        self.params: Dict[str, Any] = driver.parameters  # default values
        if parameters is not None:
            self.params.update(parameters)  # replace defaults with custom values

        # store the arguments
        self.c_pipe = command_pipe
        self.r_pipe = results_pipe
        self.run_lock = run_lock
        self.driver = driver

        # set up the internal data
        self.cd = ControllerData()

        self.current_position: int = 0
        """Where the motor is at any given moment in steps/microsteps."""

        self.target_position: int = 0
        """Where the motor should drive to (in steps/microsteps)."""

        self.microsteps: int = self.params[MICROSTEP_DEFAULT]
        """Number of microsteps per full step currently set.Default supplied by driver."""

        self.acceleration: float = self.params[ACCELERATION_RATE]
        self.deceleration: float = self.params[DECELERATION_RATE]
        self.full_steps_per_rev: int = self.params[FULL_STEPS_PER_REV]

        self.set_acceleration(self.acceleration)  # calculate c_0 from the passed acceleration

        self.move_required = False
        """Flag to indicate that the Process has received a command to move the motor"""

        self.quit_now = False
        """Flag to indicate that the Process should terminate nicely."""

        self.microstep_change_at = None
        self.microstep_new_value = None

        # do not connect to pigpio yet as pigpio uses a lock which can not be
        # pickeled and therefore not be spawned / forked.
        self.pi = None

    def run(self):
        # connect to pigpio once we have started as a process.
        # pigpio.pi can not be pickled and can therefore not be passed
        # to the stepper process.
        self.connect_pigpio()

        # Now we can initialize the driver
        self.driver.init(self.pi)

        self.idle_loop()

    def connect_pigpio(self):
        p_addr = self.params.get(PIGPIO_ADDR)
        p_port = self.params.get(PIGPIO_PORT, 8888)
        if p_addr is not None:
            self.pi = pigpio.pi(host=p_addr, port=p_port)
        else:  # use localhost or as set by OS env variable PIGPIO_ADDR / _PORT
            self.pi = pigpio.pi()

    def command_handler(self, command: Command):
        verb = command.verb
        noun = command.noun

        print(f"received verb={verb}, noun={noun}")

        if verb == Verb.SPEED:
            self.set_speed(float(noun))
        elif verb == Verb.ACCELERATION:
            self.set_acceleration(float(noun))
        elif verb == Verb.DECELERATION:
            self.set_deceleration(float(noun))
        elif verb == Verb.FULL_STEPS_PER_REV:
            self.set_full_steps_per_rev(int(noun))
        elif verb == Verb.MICROSTEPS:
            self.set_microsteps(int(noun))
        elif verb == Verb.MOVE:
            self.move(int(noun))
        elif verb == Verb.MOVE_DEG:
            self.move_deg(float(noun))
        elif verb == Verb.MOVETO:
            self.moveto(int(noun))
        elif verb == Verb.MOVETO_DEG:
            self.moveto_deg(float(noun))
        elif verb == Verb.RUN:
            self.continuous(int(noun))
        elif verb == Verb.STOP:
            self.stop()
        elif verb == Verb.ZERO:
            self.zero()
        elif verb == Verb.HARD_STOP:
            self.hard_stop()
        elif verb == Verb.QUIT:
            self.quit()
        elif verb == Verb.ENGAGE:
            self.engage()
        elif verb == Verb.RELEASE:
            self.release()
        elif verb == Verb.GET:
            self.get_value(noun)
        elif verb == Verb.NOP:
            # do nothing
            pass
        else:
            raise RuntimeError(f"Received unknown command {command}")

        # Acknowledge to the frontend that the command has been received and processed.
        self.c_pipe.send(Result(Noun.VAL_ACKNOWLEDGE, verb))

    def set_speed(self, speed):
        old_speed = self.cd.target_speed
        if speed == old_speed:
            # nothing to do here
            return

        # Check if the motor is already running
        # if yes, then accelerate / decelerate, but only if not already
        # accelerating or decelarating to a step
        if speed > old_speed and (self.cd.state == RUN or self.cd.state == DEC):
            # Austin Eq.16, Changes of acceleration
            self.cd.step = int((speed * speed) / (2.0 * self.acceleration))
            self.cd.state = INC
        elif speed < old_speed and (self.cd.state == RUN or self.cd.state == INC):
            # see above, with negative sign to cause a deceleration
            self.cd.step = int(-(speed * speed) / (2.0 * self.deceleration))
            self.cd.state = DEC

        # Set the actual target parameter
        self.cd.c_target = 1000000 / speed
        self.cd.target_speed = speed

    def set_acceleration(self, rate: float):
        # recalculate n (step) and c_0
        # See Austin Eq.15
        self.cd.step = self.cd.step * (self.acceleration / rate)
        self.cd.c_0 = 0.676 * sqrt(2.0 / rate) * 1000000
        self.acceleration = rate

    def set_deceleration(self, rate: float):
        self.deceleration = rate

    def set_full_steps_per_rev(self, steps: int):
        self.full_steps_per_rev = steps

    def set_microsteps(self, steps: int):
        c_steps = self.driver.steps_until_change_microsteps(steps)
        if c_steps < 0:
            # microstep setting not possible
            self.r_pipe.send(Result(Noun.MICROSTEP_NOT_POSSIBLE, 0))
            return

        self.microstep_new_value = steps

        if c_steps == 0:
            self._perform_microstep_change()
            change_pos = self.current_position
        else:
            change_pos = self.current_position + (c_steps * self.cd.current_direction)
            self.microstep_change_at = change_pos
            self.microstep_new_value = steps

        self.r_pipe.send(Result(Noun.MICROSTEP_CHANGE_AT, change_pos))

    def _perform_microstep_change(self):
        previous = self.microsteps
        self.microsteps = self.microstep_new_value
        factor = self.microstep_new_value / previous
        self.current_position *= factor
        self.target_position *= factor
        self.set_acceleration(self.acceleration * factor)
        self.set_deceleration(self.deceleration * factor)
        self.set_speed(self.cd.target_speed * factor)
        self.cd.step *= factor
        self.cd.c_target *= factor

        self.microstep_change_at = None

        self.driver.set_microsteps(self.microsteps)

    def move(self, relative):
        if self.target_position == float('inf') or self.target_position == float('-inf'):
            # when in continuous mode we can only reference the current position
            self.target_position = self.current_position + relative
        else:
            # otherwise reference of the current target_position.
            # when at idle this should be the same as the current_position.
            self.target_position += relative
            if relative != 0:
                self.move_required = True

    def move_deg(self, angle: float):
        steps_per_deg = (self.microsteps * self.full_steps_per_rev) / 360
        steps = round(angle * steps_per_deg)
        self.move(steps)

    def moveto(self, absolute):
        if self.target_position != absolute:
            self.target_position = absolute
            self.move_required = True

    def moveto_deg(self, angle: float):
        steps_per_rev = self.microsteps * self.full_steps_per_rev
        steps_per_deg = steps_per_rev / 360

        # from the current position remove any partial rotation
        # this new value will be the reference for the move
        current_full_rev = int(self.current_position / steps_per_rev) * steps_per_rev
        if self.current_position > 0:
            current_angle = self.current_position % steps_per_rev
        else:
            current_angle = self.current_position % -steps_per_rev

        target_steps = angle * steps_per_deg

        target_full_rev = int(target_steps / steps_per_rev) * steps_per_rev
        if angle >= 0:
            target_angle = target_steps % steps_per_rev
        else:
            target_angle = target_steps % -steps_per_rev

        if angle >= 0:
            # Clockwise move

            if target_angle >= current_angle:
                # target angle is greater than current angle, only need to add
                # full revolutions to the target angle
                target_position = target_angle
                target_position += current_full_rev + target_full_rev

            else:  # target_remainder < current_remainder
                # target angle is smaller than the current angle. For a CW move
                # we need to go the long way around to the new target
                target_position = target_angle + steps_per_rev
                target_position += current_full_rev + target_full_rev

        else:  # angle < 0
            # Counterclockwie move
            # make target angle have the same sign as current angle
            if current_angle > 0 and target_angle < 0:
                target_angle += steps_per_rev
            elif current_angle < 0 and target_angle > 0:
                target_angle -= steps_per_rev

            if target_angle <= current_angle:
                # target angle is smaller than current angle, only need to add
                # full revolutions to the target angle
                target_position = target_angle
                target_position += current_full_rev + target_full_rev

            else:  # target_remainder > current_remainder
                # target angle is greater than the current angle. For a CCW move
                # we need to go the long way around to the new target
                target_position = target_angle - steps_per_rev
                target_position += current_full_rev + target_full_rev

        self.moveto(target_position)

    def continuous(self, direction: int):
        if direction == CW:
            self.target_position = float('inf')
        else:
            self.target_position = float('-inf')

        self.move_required = True

    def stop(self):
        direction = self.cd.current_direction
        if direction == CW:
            self.target_position = self.current_position + self.cd.decel_steps
        else:
            self.target_position = self.current_position - self.cd.decel_steps

    def zero(self):
        old_target = self.target_position
        delta = old_target - self.current_position
        self.current_position = 0
        self.target_position = delta

    def hard_stop(self):
        # get the driver to stop immediately.
        self.driver.hard_stop()

        # stop the engine
        self.cd.state = STOP
        self.cd.speed = 0.0
        self.cd.step = 0

        # tbd: maybe just invalidate both as the motor might have travelled some more
        # steps before coming to a full stop
        self.target_position = self.current_position

    def quit(self):
        self.quit_now = True

    def engage(self):
        # just pass on to the driver
        self.driver.engage()

    def release(self):
        # Tell the driver to release the coils
        self.driver.release()
        self.hard_stop()  # stop any movements

    def get_value(self, noun: Noun):

        if noun == Noun.VAL_CURRENT_SPEED:
            value = self.cd.speed
        elif noun == Noun.VAL_TARGET_SPEED:
            value = self.cd.target_speed
        elif noun == Noun.VAL_CURRENT_POSITION:
            value = self.current_position
        elif noun == Noun.VAL_TARGET_POSITION:
            value = self.target_position
        elif noun == Noun.VAL_ACCELERATION:
            value = self.acceleration
        elif noun == Noun.VAL_DECELERATION:
            value = self.deceleration
        elif noun == Noun.VAL_FULL_STEPS_PER_REV:
            value = self.full_steps_per_rev
        else:
            value = None

        result = Result(noun, value)
        self.r_pipe.send(result)

    def idle_loop(self):

        try:
            while not self.quit_now:
                pipedata = self.c_pipe.poll(0.1)  # Wait for command
                if pipedata:
                    self.run_lock.acquire() # Tell the world we are busy...
                    command = self.c_pipe.recv()
                    self.command_handler(command)
                    if self.move_required:
                        self.busy_loop()
                        self.move_required = False
                    self.run_lock.release()  # ... and that we are twiddeling our thumbs again
        except EOFError:
            # the other end has closed the pipe.
            # clean up and go home
            return

    def init_move(self):
        self.driver.engage()

        steps = self.target_position - self.current_position

        if steps < 0:
            direction = CCW
        else:
            direction = CW

        self.cd.current_direction = direction
        self.driver.set_direction = direction

    def busy_loop(self):
        self.init_move()

        self.pi.wave_clear()
        prev_wave_id = -1

        # start of with a minimal delay pulse just so that we have a
        # current_wave_id. This saves one check in the loop.
        pulse = pigpio.pulse(0, 0, 100)
        self.pi.wave_add_generic([pulse])
        current_wave_id = self.pi.wave_create_and_pad(10)
        self.pi.wave_send_once(current_wave_id)

        # calculate the initial delay
        delay = self.calculate_delay()

        try:
            while not self.quit_now:

                wave = self.driver.perform_step(delay)
                self.pi.wave_add_generic(wave)
                next_wave_id = self.pi.wave_create_and_pad(10)

                #            print(f"id:{next_wave_id}, pulses: {self._pi.wave_get_pulses()}, \
                #                           duration {self._pi.wave_get_micros()}")

                self.pi.wave_send_using_mode(next_wave_id, pigpio.WAVE_MODE_ONE_SHOT_SYNC)

                # update the internal position as soon as the pulses are on
                # their way.
                if self.cd.current_direction == CW:
                    self.current_position += 1
                else:
                    self.current_position -= 1

                # check if a change in microsteps is scheduled
                if self.microstep_change_at == self.current_position:
                    self._perform_microstep_change()

                # use the time while the current and next wave are being transmitted
                # to calculate the delay of the next step
                delay = self.calculate_delay()

                if delay == 0:
                    # move finished, clean up all waves
                    while self.pi.wave_tx_busy():  # wait for all pulses to transmit
                        time.sleep(0.001)
                    self.pi.wave_clear()
                    return  # to the idle loop

                while self.pi.wave_tx_at() == current_wave_id:
                    # to keep the timing as tight as practical
                    # even at the expense of a high cpu load we just
                    # poll the command pipe and the current wave id
                    # at maximum speed and without yielding
                    if self.c_pipe.poll():
                        command = self.c_pipe.recv()
                        self.command_handler(command)

                if prev_wave_id != -1:
                    self.pi.wave_delete(prev_wave_id)

                prev_wave_id = current_wave_id
                current_wave_id = next_wave_id

            # end of loop

        except BrokenPipeError:
            # Command pipe was closed - the other end has terminated
            # close shop and go home
            return

    def calculate_delay(self) -> int:

        data = self.cd

        delta_position = self.target_position - self.current_position

        # determine the number of steps to come to a full stop from
        # the current speed. [1] Equation 16
        decel_steps = int(((data.speed * data.speed) / (2 * self.deceleration)))
        data.decel_steps = decel_steps

        if delta_position == 0 and decel_steps <= 1:
            # target position reached, move completed
            data.speed = 0.0
            data.step = 0
            data.state = STOP
            return 0

        if delta_position * data.current_direction < 0:
            # direction reversal
            data.state = DECEL
            data.step = -int(decel_steps)

        elif abs(delta_position) <= decel_steps and data.state != DECEL:
            data.state = DECEL
            data.step = -int(decel_steps)

        if data.step == 0:
            # first step or reversal infliction point
            data.c_n = data.c_0
            data.step = 1

            if data.state == DECEL:
                # 0-point of a reversal
                # officially change direction.
                if delta_position > 0:
                    data.current_direction = CW
                else:
                    data.current_direction = CCW
                self.driver.direction = data.current_direction

            data.state = ACCEL

        elif data.state == ACCEL or data.state == INC:
            data.c_n = data.c_n - ((2.0 * data.c_n) / ((4.0 * data.step) + 1))

            if data.c_n <= data.c_target:
                # selected speed reached. Change to constant speed mode.
                data.c_n = data.c_target
                data.state = RUN
            else:
                data.step += 1

        elif data.state == DECEL or data.state == DEC:
            data.c_n = data.c_n - ((2.0 * data.c_n) / ((4.0 * data.step) + 1))
            data.step += 1

        # Speed in steps per second
        data.speed = 1000000 / data.c_n

 #       print(f"{self.current_position}, {data.step}, {data.state}, {int(data.c_n)}, {int(data.speed)}, {decel_steps}")

        return int(data.c_n)
