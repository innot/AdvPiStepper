""" Stepper Driver"""
import multiprocessing
from dataclasses import dataclass
from enum import Enum, auto
from math import sqrt
from multiprocessing import Process, Pipe
from typing import Dict, Any

import pigpio

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

    target_speed: float = 0.0
    """Target speed in steps per second."""

    speed: float = 0.0
    """Current speed in steps per second."""

    step: int = 0
    """The current step in the acceleration and deceleration phases."""

    decel_steps: int = 0
    """Number of steps required to decelerate to a full stop."""


class Verb(Enum):
    # target speed
    SPEED = auto()
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

    # get value. The Noun contains the ID of the value. The value is returned via the results Pipe.
    GET = auto()

    # set value
    ACCELARATION = auto()
    DECELERATION = auto()


class Noun(Enum):
    VAL_CURRENT_SPEED = auto()
    VAL_TARGET_SPEED = auto()
    VAL_CURRENT_POSITION = auto()
    VAL_TARGET_POSITION = auto()
    VAL_ACCELERATION = auto()
    VAL_DECELERATION = auto()


@dataclass
class Command(object):
    """Command object passed from the Frontend to the background Process."""
    verb: Verb = None
    noun: Noun = None

    def __init__(self, verb: Verb, noun: Noun):
        self.verb = verb
        self.noun = noun


@dataclass
class Result(object):
    """Result object passed from the background Process to the frontend."""
    noun: Noun = None
    value = None

    def __init__(self, noun: Noun, value):
        self.noun = noun
        self.value = value


@dataclass
class Statistics(object):
    number_of_steps: int = 0
    runtime: int = 0


class AdvPigpioStepper(object):
    """
    classdocs
    """

    def __init__(self, pi=None, driver=None):
        """
        :param pi: 'obj':pigpio.pi
            pigpio instance to use. If not given, the local pigpio
            demon is used.

        :param driver: 'obj':BaseDriver
            The GPIO driver used to translate steps to pigpio pulses
            and waves. The stepper may contain some optional info
            about the actual stepper motor (max. speed etc.)
            Defaults to a debug stepper (no actual gpio).

        """

        if pi is None:
            pi = pigpio.pi()

        if driver is None:
            driver = DriverBase()

        # initialize the driver
        driver.init(pi)

        # Get the default speed/accel/decel parameters from the driver
        params = driver.parameters

        c_pipe_remote, self.c_pipe = multiprocessing.Pipe()
        self.r_pipe, r_pipe_remote = multiprocessing.Pipe()

        self.process = StepperProcess(c_pipe_remote, r_pipe_remote, driver, pi, params)

    @property
    def target_speed(self) -> float:
        """
        Get the selected target speed. During acceleration / deceleration
        the actual speed may be less than the target speed.
        :return: The speed in steps or microsteps per second
        :rtype: float
        """
        result = float(self._get_value(Noun.VAL_TARGET_SPEED))
        return result

    @target_speed.setter
    def target_speed(self, speed: float):
        """ Set the target speed. This is the speed the controller will
        accelerate to and maintain once reached. The speed is 
        independent from the direction, therefore the speed must be
        greater than 0.

        :param speed: target speed in steps/microsteps per second.
        :type speed: float
        :raises ValueError: When the given speed is 0 or less.
        """
        if speed <= 0.0:
            raise ValueError(f"Speed must be > 0.0, was {speed}")

        cmd = Command(Verb.SPEED, speed)
        self.c_pipe.send(cmd)

    @property
    def current_speed(self) -> float:
        """
        Get the current speed. During acceleration / deceleration
        the current speed may be less than the target speed.
        :return: The speed in steps or microsteps per second
        :rtype: float
        """
        result = self._get_value(Noun.VAL_CURRENT_SPEED)
        return float(result)

    @property
    def acceleration(self) -> float:
        """Get the current acceleration.
        :return: The set acceleration in steps per second squared.
        :rtype: float"""
        result = self._get_value(Noun.VAL_ACCELERATION)
        return float(result)

    @acceleration.setter
    def acceleration(self, rate):
        """Sets the desired acceleration in steps per second squared.

        High values may cause lost steps and stalled motors

        :param rate: Must be greater than 0.
        :type rate: float
        :raises ValueError: if the rate is not valid.
        """

        if rate <= 0.0:
            raise ValueError(f"Acceleration must be greater than 0.0, was {rate}")

        cmd = Command(Verb.ACCELARATION, rate)
        self.c_pipe.send(cmd)

    @property
    def deceleration(self):
        """Get the current deceleration.
        :return: The set deceleration in steps per second squared.
        :rtype: float"""
        result = self._get_value(Noun.VAL_DECELERATION)
        return float(result)

    @deceleration.setter
    def deceleration(self, rate):
        """Sets the desired deceleration in steps per second squared.

        High values may cause lost steps due to motor inertia.

        :param rate: Must be greater than 0.
        :type rate: float
        :raises ValueError: if the rate is not valid.
        """

        if rate <= 0.0:
            raise ValueError(f"Deceleration must be greater than 0.0, was {rate}")

        cmd = Command(Verb.DECELARATION, rate)
        self.c_pipe.send(cmd)

    @property
    def full_steps_per_rev(self):
        """
        Returns
        -------
             the number of full steps per full revolution.
        """
        return self._full_steps_per_rev

    @full_steps_per_rev.setter
    def full_steps_per_rev(self, steps):
        """Set the number of full steps for one complete revolution.

        Parameters
        ----------
        steps : int
            must be equal or greater than 2.
        """
        if steps < 2:
            raise ValueError("steps must be 2 or greater")

        self._full_steps_per_rev = steps

    @property
    def microsteps(self):
        """
        :returns: currently set number of microsteps.
        :rtype: int"""

        return self._microsteps

    @microsteps.setter
    def microsteps(self, steps):
        """
        Set number of microsteps per full step.
        :param steps: 
        """
        if steps not in self._microstep_options:
            raise ValueError("Given microstep setting is not valid")

        self._driver.microsteps = steps

    def move(self, relative, speed=0):
        """
        Move the given number of steps. Positiv for forward, negative for backwards.
        This call blocks until all steps have been performed.
        """
        if speed == 0:
            speed = self._param.max_speed

        self._target_position = self._current_position + relative
        self.speed = speed
        self._init_move(relative, speed)
        self._main_loop()

    def move_to(self, absolut):
        """
        Move to the given location. Use set_zero() to define the origin.
        This function blocks until all steps have been performed."""
        pass

    def engage(self):
        self._driver.engage()

    def disengage(self):
        self._driver.release()

    def _get_value(self, noun: Noun):
        """Retrieve the given parameter from the stepper process.
        This method blocks until the value is returned by the process, but
        not longer than 1 second (responses time should be in the
        sub-microsecond range.

        :param noun: The parameter to fetch.
        :type noun: Noun.
        :return: The requested value.
        :rtype: object"""

        cmd = Command(Verb.GET, noun)
        self.c_pipe.send(cmd)
        self.r_pipe.poll(1)  # if no result after 1 second then the other Process is stuck
        result = self.r_pipe.recv()
        if result.noun != noun:
            # todo do something with the unexpected result
            print(f"received unexpected result {result}")
        else:
            return result.value

    def _init_move(self, steps, speed):

        self._driver.engage()

        if steps < 0:
            self._cd.current_direction = CCW
            steps = -steps
        else:
            self._cd.current_direction = CW

        self._driver.set_direction(self._cd.current_direction)


class StepperProcess(Process):

    def __init__(self, command_pipe: Pipe, results_pipe: Pipe, driver: DriverBase, pi: pigpio.pi,
                 parameters: Dict[str, Any] = None):
        super(StepperProcess, self).__init__()

        # store the arguments
        self.c_pipe: Pipe = command_pipe
        self.r_pipe: Pipe = results_pipe
        self.driver = driver
        self.pi = pi

        self.params: Dict[str, Any] = driver.parameters  # default values
        if parameters is not None:
            self.params.update(parameters)  # replace defaults with custom values

        # set up the internal data
        self.cd = ControllerData()

        self.current_position: int = 0
        """Where the motor is at any given moment in steps/microsteps."""

        self.target_position: int = 0
        """Where the motor should drive to (in steps/microsteps)."""

        self.microsteps: int = 1
        """Number of microsteps per full step currently set.
        1 means no microstepping (default).
        """

        self.accel: float = self.params[ACCELERATION_RATE]
        self.decel: float = self.params[DECELERATION_RATE]
        self.full_steps_per_rev: int = self.params[FULL_STEPS_PER_REV]

        self.acceleration(self.accel)  # calculate c_0 from the passed acceleration

        self.move_required = False
        """Flag to indicate that the Process has received a command to move the motor"""

    def run(self):

        self.idle_loop()

    def idle_loop(self):

        while True:  # TODO implement some flag to quit this loop and the whole process
            command = self.c_pipe.poll(None)  # Wait for command
            self.command_handler(command)
            if self.move_required:
                self.busy_loop()
                self.move_required = False  # Busy_loop only returns when the motor has stopped.

    def busy_loop(self):
        while True:
            if self.c_pipe.poll():
                command = self.c_pipe.recv()
                self.command_handler(command)

    def command_handler(self, command: Command):
        verb = command.verb
        noun = command.noun

        if verb == Verb.SPEED:
            self.speed(float(noun))
        elif verb == Verb.ACCELARATION:
            self.acceleration(float(noun))
        elif verb == Verb.DECELERATION:
            self.deceleration(float(noun))
        elif verb == Verb.MOVE:
            self.move(int(noun))
        elif verb == Verb.MOVE_DEG:
            self.move_deg(float(noun))
        elif verb == Verb.MOVETO:
            self.moveto(int(noun))
        elif verb == Verb.MOVETO_DEG:
            self.moveto_deg(float(noun[0]))
        elif verb == Verb.RUN:
            self.continous(int(noun[1]))
        elif verb == Verb.STOP:
            self.stop()
        elif verb == Verb.Zero:
            self.zero()
        elif verb == Verb.HARD_STOP:
            self.hard_stop()
        elif verb == Verb.GET:
            self.get_value(noun)
        else:
            raise RuntimeError(f"Received unknown command {command}")

    def speed(self, speed):
        old_speed = self.cd.target_speed
        if speed == old_speed:
            # nothing to do here
            return

        # Check if the motor is already running
        # if yes, then accelerate / decelerate, but only if not already
        # accelerating or decelarating to a step
        if speed > old_speed and (self.cd.state == RUN or self.cd.state == DEC):
            # Austin Eq.16, Changes of accelaration
            self.cd.step = (speed * speed) / (2.0 * self.accel)
            self.cd.state = INC
        elif speed < old_speed and self.cd.state != DECEL:
            # see above, with negativ sign to cause a deceleration
            self.cd.step = -(speed * speed) / (2.0 * self.decel)
            self.cd.state = DEC

        # Set the actual target parameter
        self.cd.c_target = 1000000 / speed
        self.cd.target_speed = speed

    def acceleration(self, rate: float):
        # recalculate n (step) and c_0
        # See Austin Eq.15
        self.cd.step = self.cd.step * (self.accel / rate)
        self.cd.c_0 = 0.676 * sqrt(2.0 / rate) * 1000000
        self.accel = rate

    def deceleration(self, rate: float):
        self.decel = rate

    def move(self, relative):
        self.target_position = self.current_position + relative
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

    def continous(self, direction: int):
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
        # todo implement hard stop
        self.driver.hard_stop()

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
            value = self.params[ACCELERATION_RATE]
        elif noun == Noun.VAL_DECELERATION:
            value = self.params[DECELERATION_RATE]
        else:
            value = None

        result = Result(noun, value)
        self.r_pipe.send(result)

    def busy_loop(self):

        self.pi.wave_clear()
        next_wave_id = -1
        current_wave_id = -1
        prev_wave_id = -1

        # start of with a minimal delay pulse just so that we have a
        # current_wave_id. This saves one check in the loop.
        pulse = pigpio.pulse(0, 0, 100)
        self.pi.wave_add_generic([pulse])
        current_wave_id = self.pi.wave_create_and_pad(10)
        self.pi.wave_send_once(current_wave_id)

        # calculate the initial delay
        delay = self.calcuate_delay()

        while True:

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

            # use the time while the current and next wave are being transmitted
            # to calculate the delay of the next step
            delay = self.calcuate_delay()

            while self.pi.wave_tx_at() == current_wave_id:
                pass
                # try to keep the timing as tight as practical
                # even at the expense of a high cpu load
                # Alternative: time.sleep(0.0001)

            if prev_wave_id != -1:
                self.pi.wave_delete(prev_wave_id)

            if delay == 0:
                # move finished
                # TODO: clean up
                return

            prev_wave_id = current_wave_id
            current_wave_id = next_wave_id

        # end of loop

    def calcuate_delay(self) -> int:

        data = self.cd

        delta_position = self.target_position - self.current_position

        # determine the number of steps to come to a full stop from
        # the current speed. [1] Equation 16
        decel_steps = int(((data.speed * data.speed) / (2 * self.decel)) + 0.5)
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
            # first step or reversal infection point
            data.c_n = data.c_0
            data.step = 1

            if data.state == DECEL:
                # 0-point of a reversal
                # officially change direction.
                if delta_position > 0:
                    data.current_direction = CW
                else:
                    data.current_direction = CCW
                self.driver.set_direction(data.current_direction)

            data.state = ACCEL

        elif data.state == ACCEL:
            data.c_n = data.c_n - ((2.0 * data.c_n) / ((4.0 * data.step) + 1))

            if data.c_n <= data.c_target:
                # selected speed reached. Change to constant speed mode.
                data.c_n = data.c_target
                data.state = RUN
            else:
                data.step += 1

        elif data.state == DECEL:
            data.c_n = data.c_n - ((2.0 * data.c_n) / ((4.0 * data.step) + 1))
            data.step += 1

        # Speed in steps per second
        data.speed = 1000000 / data.c_n

        print(f"{delta_position}, {data.step}, {data.state}, {int(data.c_n)}, {int(data.speed)}, {decel_steps}")

        return int(data.c_n)
