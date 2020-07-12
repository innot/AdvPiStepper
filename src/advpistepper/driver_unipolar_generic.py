from .driver_base import *

WAVE = 0
FULLSTEP = 1
HALFSTEP = 2


class UnipolarDriver(DriverBase):
    defaults: Dict[str, Any] = {
        MAX_SPEED: 1000.0,
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
        """
        :param a1: GPIO pin number for coil A+ (pigpio numbering)
        :type a1:int
        :param a2: GPIO pin number for coil A- (pigpio numbering)
        :type a2:int
        :param b1: GPIO pin number for coil B+ (pigpio numbering)
        :type b1:int
        :param b2: GPIO pin number for coil B- (pigpio numbering)
        :type b2:int
        :param parameters: Optional parameters to override the default values.
        :type parameters: dict, optional
        """

        p: Dict[str, Any] = self.defaults  # default values
        if parameters is not None:
            p.update(parameters)  # replace defaults with custom values

        super().__init__(p)

        # : in the order A+, B+, A-, B-. This order is different from the
        # gpio_pins property because stepper motor wires are usually 
        # documented as A+,A-,B+,B- while the stepper sequence looks 
        # better, i.e. like a circulating wave in the A+,B+.A-,B- order.   
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
    def gpio_pins(self):
        """Get the currently assign GPIO pins.
        :return: The currently assigned pins, in order A+, A-, B+ and B-.
        :rtype: tuple
        """
        return (self._gpio_pins[0], self._gpio_pins[2],
                self._gpio_pins[1], self._gpio_pins[3])

    @gpio_pins.setter
    def gpio_pins(self, pins: tuple):
        """
        Assign the GPIO pins to use.
        
        :param pins:
            Tuple with the 4 gpio pin numbers (Broadcom numbering) in 
            the order A+, A-, B+ and B-
        :type pins: tuple
        :raises ValueError: if pins is not 4 valid pin numbers.
        """
        if len(pins) != 4:
            raise ValueError(f"Wrong number of pins. Must be 4, was {len(pins)}")

        for pin in pins:
            if not isinstance(pin, int) or pin < 0:
                raise ValueError(f"Invalid pin number {pin} in {pins}")

        a1, a2, b1, b2 = pins
        self._gpio_pins = (a1, b1, a2, b2)
        self._gpio_pins_masks = (1 << a1, 1 << b1, 1 << a2, 1 << b2)

    def init(self, pi: pigpio.pi):
        """Initialize the driver by setting all GPIO pins to output and to LOW.
        :param pi: the pigpio instance to use.
        """
        super().init(pi)

        for pin in self._gpio_pins:
            pi.set_mode(pin, pigpio.OUTPUT)
            pi.write(pin, 0)

        # initialize the sequencer
        self._current_step = 0
        self._current_direction = CW

    def engage(self):
        """Energize the coils."""

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

    def set_microsteps(self, microsteps: int) -> bool:
        if microsteps == HALFSTEP:
            if self._microsteps != HALFSTEP:
                self._microsteps = microsteps
                self._current_step *= 2
            return True

        elif microsteps == FULLSTEP or microsteps == WAVE:
            if self._microsteps == HALFSTEP:
                if self._current_step % 2 == 1:  # odd set, can't change
                    return False
                else:
                    self._microsteps = microsteps
                    self._current_step /= 2
                return True
            else:  # FULLSTEP or WAVE already
                return True
        else:
            # unsupported microstep value
            return False

    def steps_until_change_microsteps(self, microsteps: int) -> int:
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

    def set_direction(self, direction: int):
        self._current_direction = direction

    def perform_step(self, delay: int) -> list:

        direction = self._current_direction

        next_step = (self._current_step + direction) % len(self._sequences[self._microsteps])
        curr_seq = self._sequences[self._microsteps][self._current_step]
        next_seq = self._sequences[self._microsteps][next_step]
        self._current_step = next_step

        wave = []
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

        wave.append(pigpio.pulse(0, 0, delay))

        #        print(f"seq[{next_step}] = {next_seq} @ {t.perf_counter_ns()}")

        return wave
