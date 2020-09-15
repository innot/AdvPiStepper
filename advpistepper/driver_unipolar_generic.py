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
Driver for generic Unipolar Stepper Motors.

Baseclass for all `unipolar <https://en.wikipedia.org/wiki/Stepper_motor#Unipolar_motors>`__
motor drivers, but can also be used by itself.
It generates the GPIO sequences for eiter FULLSTEP mode, where two coils
are powered for each step, or HALFSTEP mode, wher either one or two coils
are powered at each step.

Unless overridden by a subclass or by the user this driver uses the following
default parameters:

- MAX_SPEED: 800 steps/second (120rpm)
- MAX_TORQUE_SPEED: 100 steps/second
- ACCELERATION_RATE: 2000 steps / second^2
- DECELERATION_RATE: 3000 steps / second^2
- FULL_STEPS_PER_REV: 200 Full steps per revolution (1.8° per step)
- MICROSTEP_OPTIONS: FULLSTEP or HALFSTEP.
- MICROSTEP_DEFAULT: FULLSTEP

Besides the (optional) parameters this driver needs the the 4 GPIO pins connected to
the A+, A-, B+ and B- coils (called a1, a2, b1 and b2 by the driver)

.. note::
    Except for very low power stepper motors the motor wires should not be connected
    to the Raspberry directly. To provide sufficient power to the motor a driver like
    the `ULN2003A <https://en.wikipedia.org/wiki/ULN2003A>`__ should be used.

"""

from .driver_base import *

WAVE = 0
FULLSTEP = 1
HALFSTEP = 2


class UnipolarDriver(DriverBase):
    """
    Basic Unpolar driver module.

    :param a1: GPIO pin number for coil A+ (pigpio/broadcom numbering)
    :type a1: int
    :param a2: GPIO pin number for coil A- (pigpio/broadcom numbering)
    :type a2: int
    :param b1: GPIO pin number for coil B+ (pigpio/broadcom numbering)
    :type b1: int
    :param b2: GPIO pin number for coil B- (pigpio/broadcom numbering)
    :type b2: int
    :param parameters: Optional parameters to override the default values.
    :type parameters: dict, optional

    """

    _unipolar_generic_defaults: Dict[str, Any] = {
        DRIVER_NAME: "Generic Unipolar",
        MAX_SPEED: 800.0,
        MAX_TORQUE_SPEED: 100.0,
        ACCELERATION_RATE: 2000,
        DECELERATION_RATE: 3000,
        FULL_STEPS_PER_REV: 400,
        MICROSTEP_OPTIONS: (FULLSTEP, HALFSTEP),
        MICROSTEP_DEFAULT: FULLSTEP
    }

    _sequences = [3]

    # The wave sequence has less torque at the same speed as the FULLSTEP sequence
    # Not really useful IMHO, included just for completeness.
    _sequences.insert(WAVE, [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])

    _sequences.insert(FULLSTEP, [
        [1, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 1],
        [1, 0, 0, 1]
    ])

    # : Step Sequence table.
    _sequences.insert(HALFSTEP, [
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 0],
    ])

    def __init__(self, a1, a2, b1, b2, parameters: Dict[str, Any] = None):

        p: Dict[str, Any] = self._unipolar_generic_defaults  # default values
        if parameters is not None:
            p.update(parameters)  # replace defaults with custom values

        super().__init__(p)

        self._gpio_pins = [0, 0, 0, 0]

        # and the associated masks for the pulses
        self._gpio_pins_masks = [0, 0, 0, 0]

        self.gpio_pins = (a1, a2, b1, b2)

        # : Number of microsteps. For the unipolar driver this is either 1 or 2
        self._microsteps = p[MICROSTEP_DEFAULT]

        # GPIO state
        self._engaged = False

        # Current point in the sequence
        self._current_step = 0
        self._current_direction = CW

    @property
    def gpio_pins(self) -> tuple:
        """Tupel with the four GPIO pins used by the driver.
        The are in the order A+, A-, B+ and B- and use the Broadcom pin
        numbering as used by pigpio.
        This property can be written to, however changing the GPIO pins
        while the motor is running is propably not a good idea.

        :Type: Tupel with 4 int, 0 <= n <= 56
        """
        return (self._gpio_pins[0], self._gpio_pins[2],
                self._gpio_pins[1], self._gpio_pins[3])

    @gpio_pins.setter
    def gpio_pins(self, pins: tuple):
        if len(pins) != 4:
            raise ValueError(f"Wrong number of pins. Must be 4, was {len(pins)}")

        for pin in pins:
            if not isinstance(pin, int) or pin < 0:
                raise ValueError(f"Invalid pin number {pin} in {pins}")

        # Store in the order A+, B+, A-, B-. This order is different from the
        # gpio_pins property because stepper motor wires are usually
        # documented as A+,A-,B+,B- while the stepper sequence looks
        # better, i.e. like a circulating wave in the A+,B+.A-,B- order.
        a1, a2, b1, b2 = pins
        self._gpio_pins = (a1, b1, a2, b2)
        self._gpio_pins_masks = (1 << a1, 1 << b1, 1 << a2, 1 << b2)

    def init(self, pi: pigpio.pi):
        """Initialize the driver by setting all GPIO pins to output and to LOW.
        This method should only be called by the stepper process.

        :param pi: the pigpio instance to use.
        """
        super().init(pi)  # The parent class keeps the pigpio instance for us.

        for pin in self._gpio_pins:
            pi.set_mode(pin, pigpio.OUTPUT)
            pi.write(pin, 0)

        # initialize the sequencer
        self._current_step = 0
        self._current_direction = CW

    def engage(self):
        """Energize the coils.
        Only the coils for the current step are energized,
        the other coils will not be powered.
        """

        # First set up the GPIO pins as output
        for pin in self._gpio_pins:
            self._pi.set_mode(pin, pigpio.OUTPUT)

        # Determine which pins should be active at the moment
        step = self._sequences[self._microsteps][self._current_step]

        # and set them all
        for i in range(0, len(step)):
            pin = self._gpio_pins[i]
            level = step[i]
            self._pi.write(pin, level)


    def release(self):
        """Deenergize all coils."""
        for pin in self._gpio_pins:
            self._pi.write(pin, 0)

    def set_microsteps(self, steps: int) -> bool:
        """
        Set the microsteps.

        This method will only be successful if the driver is ready for a change in
        microsteps, which can be checked with :meth:`steps_until_change_microsteps` method.

        :param steps: either FULLSTEP (1) or HALFSTEP (2)
        :type steps: int
        :return: 'True' if the change was successfull, 'False' if the microsteps could not be changed.
        """
        if steps == HALFSTEP:
            if self._microsteps != HALFSTEP:
                self._microsteps = steps
                self._current_step = int(self._current_step * 2)
            return True

        elif steps == FULLSTEP or steps == WAVE:
            if self._microsteps == HALFSTEP:
                if self._current_step % 2 == 1:  # odd set, can't change
                    return False
                else:
                    self._microsteps = steps
                    self._current_step = int(self._current_step / 2)
                return True
            else:  # FULLSTEP or WAVE already
                return True
        else:
            # unsupported microstep value
            return False

    def steps_until_change_microsteps(self, microsteps: int) -> int:
        """Checks when the the requested microstep setting can be changed.

        The result is in steps. If the result is 0 the driver is ready for a
        change in microsteps. Positive values are the number of steps which have
        to be performed before the change is possible (e.g. to sync to the next
        full step first). A negative return value means that the driver can not change
        to the new value, either because it is not supported or the change can only be
        made when the motor is not running.

        :param microsteps: Requested microstep option, either FULLSTEP (1) or HALFSTEP (2)
        :type microsteps: int
        :returns: Either 0 (change possible right now) or 1 (change possibel after the next step).
            Negative if microstep was neither 1 nor 2.
        :rtype: int
        """
        if microsteps == HALFSTEP:
            # microsteps can be changed to HALFSTEP anytime without problems
            return 0
        else:
            # FULLSTEP or WAVE requested.
            if self._microsteps == WAVE or self._microsteps == FULLSTEP:
                # We are already in either mode. Change will have no effect and is posible anytime
                return 0
            else:  # Change from Halfstep to Fullstep
                # is only possible at even steps (0, 2, 4, 6)
                return self._current_step % 2

    @DriverBase.direction.setter
    def direction(self, direction: int):
        self._current_direction = direction

    def perform_step(self, delay: int) -> list:
        """Generate the pigpio wave list for a single step.

        The generated wave starts with the given delay and then sets the GPIOs
        for the step.
        """

        direction = self._current_direction

        next_step = (self._current_step + direction) % len(self._sequences[self._microsteps])
        curr_seq = self._sequences[self._microsteps][self._current_step]
        next_seq = self._sequences[self._microsteps][next_step]
        self._current_step = next_step

        # start with a delay, because a move starts with a call to engage() which sets the
        # GPIOs to the current step
        wave = [pigpio.pulse(0, 0, delay)]

        for i in range(0, len(curr_seq)):
            if curr_seq[i] == next_seq[i]:
                continue

            if curr_seq[i] == 1:
                # a currently set pin needs to be switched off
                pin_off = self._gpio_pins_masks[i]
                wave.append(pigpio.pulse(0, pin_off, 0))

            else:
                # a currently unset pin needs to be switched on
                pin_on = self._gpio_pins_masks[i]
                wave.append(pigpio.pulse(pin_on, 0, 0))

        return wave

    def hard_stop(self):
        """Perform a hard stop where the motor is stop immediately, even
        at the expense of lost steps.
        This is done by pulling all 4 GPIO pins to LOW and changing the pins to input
        to prevent any steps which are still in the pipeline to go to the motor.
        """
        for pin in self._gpio_pins:
            self._pi.write(pin, 0)
            self._pi.set_mode(pin, pigpio.INPUT)
