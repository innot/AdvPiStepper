#  Copyright (c) 2020 Thomas Holland (thomas@innot.de)
#  All rights reserved.
#
#  This code is licensed under the MIT License.
#
#  Refer to the LICENSE file which is part of the AdvPiStepper distribution or
#  to https://opensource.org/licenses/MIT for a text of the license.
#

import sys
from unittest import TestCase

from advpistepper.stepper import *


class TestStepperProcess(TestCase):
    c_pipe = None
    r_pipe = None

    def setUp(self) -> None:

        driver = DriverBase()

        c_pipe_remote, self.c_pipe = multiprocessing.Pipe()
        self.r_pipe, r_pipe_remote = multiprocessing.Pipe()

        self.process = StepperProcess(c_pipe_remote, r_pipe_remote, driver)

    def test_speed(self):
        print("Test Command SPEED")
        for i in range(1, 1000, 100):
            self.process.speed(i)
            self.assertEqual(i, self.process.cd.target_speed)
            self.assertEqual(1000000 / i, self.process.cd.c_target)

        # fake a running stepper at 1000 hz
        self.process.cd.c_n = 1000
        self.process.cd.state = RUN
        self.process.cd.step = 100

        # test acceleration
        self.process.speed(2000)
        self.assertEqual(INC, self.process.cd.state)
        self.assertEqual((2000 * 2000) / (2 * self.process.accel), self.process.cd.step)

        # ... and deceleration
        self.process.speed(1000)
        self.assertEqual(self.process.cd.state, DEC)
        self.assertEqual(self.process.cd.step, -(1000 * 1000) / (2 * self.process.decel))

    def test_acceleration(self):
        print("Test Command ACCELERATION")

        self.process.cd.step = 0  # should be 0, but just in case...
        rate = 1000
        self.process.acceleration(rate)
        self.assertEqual(self.process.cd.step, 0)
        self.assertEqual(self.process.cd.c_0, 0.676 * sqrt(2.0 / rate) * 1000000)
        self.assertEqual(self.process.accel, rate)

        self.process.cd.step = 10
        rate = 2000
        self.process.acceleration(rate)
        self.assertEqual(self.process.cd.step, 10 * (1000 / rate))
        self.assertEqual(self.process.cd.c_0, 0.676 * sqrt(2.0 / rate) * 1000000)
        self.assertEqual(self.process.accel, rate)

    def test_deceleration(self):
        print("Test Command DECELERATION")
        self.process.deceleration(1234)
        self.assertEqual(self.process.decel, 1234)

    def test_move(self):
        print("Test Command MOVE")
        self.process.move(0)
        self.assertEqual(self.process.target_position, 0)
        self.assertFalse(self.process.move_required)
        self.process.move(100)
        self.assertEqual(self.process.target_position, 100)
        self.assertTrue(self.process.move_required)
        self.process.current_position = 100  # simulate that the move has completed
        self.process.move(-200)
        self.assertEqual(self.process.target_position, -100)
        self.assertTrue(self.process.move_required)

        # microsteps should not affect a normal move
        self.process.zero()
        self.process.current_position = 0
        self.process.microsteps = 10  # arbitrary and just for convenience
        self.process.move(999)
        self.assertEqual(self.process.target_position, 999)

    def test_move_deg(self):
        print("Test Command MOVE_DEG")
        self.process.full_steps_per_rev = 360  # just for convenience

        self.process.move_deg(0)
        self.assertEqual(self.process.target_position, 0)
        self.assertFalse(self.process.move_required)
        self.process.move_deg(45)
        self.assertEqual(self.process.target_position, 45)
        self.assertTrue(self.process.move_required)
        self.process.current_position = 45  # simulate that the move has completed
        self.process.move_deg(-90)
        self.assertEqual(self.process.target_position, -45)
        self.assertTrue(self.process.move_required)

        # microstepping should affect the move_deg
        self.process.zero()
        self.process.current_position = 0
        self.process.microsteps = 10  # again, arbitrary and just for convenience
        self.process.move_deg(45)
        self.assertEqual(self.process.target_position, 450)
        self.process.current_position = 450  # simulate that the move has completed
        self.process.move_deg(-90)
        self.assertEqual(self.process.target_position, -450)

    def test_moveto(self):
        print("Test Command MOVETO")
        self.process.moveto(0)
        self.assertEqual(self.process.target_position, 0)
        self.assertFalse(self.process.move_required)
        self.process.moveto(123)
        self.assertEqual(self.process.target_position, 123)
        self.assertTrue(self.process.move_required)
        self.process.current_position = 123  # simulate that the move has completed
        self.process.moveto(-234)
        self.assertEqual(self.process.target_position, -234)
        self.assertTrue(self.process.move_required)

    def test_moveto_deg(self):
        print("Test Command MOVETO_DEG")
        self.process.full_steps_per_rev = 360  # just for convenience

        self.process.moveto_deg(0)
        self.assertEqual(self.process.target_position, 0)
        self.assertFalse(self.process.move_required)

        self.process.current_position = 900  # 2,5 revolutions, 6 o'clock position

        self.process.moveto_deg(90)  # Move CW to 3 o'clock position
        self.assertEqual(3 * 360 + 90, self.process.target_position)
        self.assertTrue(self.process.move_required)

        self.process.moveto_deg(-270)  # move CCW to 3 o'clock position
        self.assertEqual(2 * 360 + 90, self.process.target_position)
        self.assertTrue(self.process.move_required)

        self.process.moveto_deg(270)  # move CW to 9 o'clock position
        self.assertEqual(2 * 360 + 270, self.process.target_position)
        self.assertTrue(self.process.move_required)

        self.process.moveto_deg(-90)  # move CCW to 9 o'clock position
        self.assertEqual(2 * 360 - 90, self.process.target_position)
        self.assertTrue(self.process.move_required)

        # test moves > 360°
        self.process.current_position = 360
        self.process.moveto_deg(720)
        self.assertEqual(3 * 360, self.process.target_position)

        self.process.moveto_deg(-720)
        self.assertEqual(-1 * 360, self.process.target_position)

        self.process.current_position = 90
        self.process.moveto_deg(89 + 360)  # CW to 89° (rel 359°) + 1 full rev (360°)
        self.assertEqual(2 * 360 + 89, self.process.target_position)

        self.process.current_position = 90
        self.process.moveto_deg(90 + 360)  # CW to 90° (rel 0°) + 1 full rev (360°)
        self.assertEqual(1 * 360 + 90, self.process.target_position)

        self.process.current_position = 90
        self.process.moveto_deg(91 + 360)  # CW to 90° (rel 1°) + 1 full rev (360°)
        self.assertEqual(1 * 360 + 91, self.process.target_position)

        # CCW move > 360°

        self.process.current_position = -90
        self.process.moveto_deg(-89 - 360)  # CCW to 271° (rel 359°) + 1 full rev (360°)
        self.assertEqual(2 * -360 - 89, self.process.target_position)

        self.process.current_position = -90
        self.process.moveto_deg(-90 - 360)  # CCW to 270° (rel 0°) + 1 full rev (360°)
        self.assertEqual(1 * -360 - 90, self.process.target_position)

        self.process.current_position = -90
        self.process.moveto_deg(-91 - 360)  # CCW to 269° (rel 1°) + 1 full rev (360°)
        self.assertEqual(1 * -360 - 91, self.process.target_position)

        # microstepping should affect the move_deg
        self.process.zero()
        self.process.current_position = 500  # arbitrary angle less than 1 rev
        self.process.microsteps = 10  # again, arbitrary and just for convenience
        self.process.moveto_deg(180)
        self.assertEqual(1800, self.process.target_position)
        self.process.moveto_deg(-180)
        self.assertEqual(-1800, self.process.target_position)

    def test_continous(self):
        print("Test Command CONTINUOUS")

        self.process.continous(CW)
        self.assertEqual(float('inf'), self.process.target_position)
        # check that the delay calculation works with infinity
        delay = self.process.calcuate_delay()
        self.assertTrue(0 < delay < sys.maxsize)
        self.assertEqual(ACCEL, self.process.cd.state)

        # reset state
        self.process.cd = ControllerData()

        self.process.continous(CCW)
        self.assertEqual(float('-inf'), self.process.target_position)
        delay = self.process.calcuate_delay()
        self.assertTrue(0 < delay < sys.maxsize)
        self.assertEqual(ACCEL, self.process.cd.state)

    def test_init_move(self):
        print("Test init_move()")

        self.process.current_position = 1
        self.process.target_position = 2
        self.process.init_move()
        self.assertEqual(CW, self.process.cd.current_direction)

        self.process.target_position = 0
        self.process.init_move()
        self.assertEqual(CCW, self.process.cd.current_direction)

        self.process.current_position = -1
        self.process.target_position = -2
        self.process.init_move()
        self.assertEqual(CCW, self.process.cd.current_direction)

        self.process.target_position = 0
        self.process.init_move()
        self.assertEqual(CW, self.process.cd.current_direction)

    def test_stop(self):
        print("Test Command STOP")
        # fake a move
        self.process.cd.current_direction = CW
        self.process.cd.state = ACCEL
        self.process.cd.c_n = 1000
        self.process.cd.step = 1000
        self.process.cd.speed = 1000

        self.process.target_position = 123456
        self.process.current_position = 0
        self.process.calcuate_delay()

        self.process.stop()
        self.assertEqual(self.process.cd.decel_steps, self.process.target_position)

        # CCW
        self.process.cd.current_direction = CCW
        self.process.target_position = -123456
        self.process.current_position = 0
        self.process.calcuate_delay()

        self.process.stop()
        self.assertEqual(-self.process.cd.decel_steps, self.process.target_position)

    def test_zero(self):
        print("Test Command ZERO")
        self.process.current_position = -1000
        self.process.target_position = 1000
        self.process.zero()
        self.assertEqual(0, self.process.current_position)
        self.assertEqual(2000, self.process.target_position)

        self.process.current_position = 1000
        self.process.target_position = -1000
        self.process.zero()
        self.assertEqual(0, self.process.current_position)
        self.assertEqual(-2000, self.process.target_position)

    def test_hardstop(self):
        print("Test Command HARDSTOP")
        # fake a running stepper at 1000 hz
        self.process.cd.c_n = 1000
        self.process.cd.state = RUN
        self.process.cd.step = 100

        self.process.hard_stop()

        self.assertEqual(STOP, self.process.cd.state)
        self.assertEqual(0.0, self.process.cd.speed)
        self.assertEqual(0, self.process.cd.step)
        self.assertEqual(self.process.target_position, self.process.current_position)

    def test_get_value_target_speed(self):
        print("Test get_value() TARGET_SPEED")
        self.process.start()
        self.c_pipe.send(Command(Verb.SPEED, 123.0))
        self.c_pipe.send(Command(Verb.GET, Noun.VAL_TARGET_SPEED))
        if not self.r_pipe.poll(10):  # the first command to result round trip is somehow sometimes very slow
            self.fail()
        result = self.r_pipe.recv()
        self.assertEqual(Noun.VAL_TARGET_SPEED, result.noun)
        self.assertEqual(123.0, result.value)
        self.c_pipe.send(Command(Verb.QUIT, 0))
        self.process.join()

    def test_get_value_current_speed(self):
        print("Test get_value() CURRENT_SPEED")
        self.process.start()
        self.c_pipe.send(Command(Verb.SPEED, 20.0))
        self.c_pipe.send(Command(Verb.MOVETO, 100))
        time.sleep(0.1)
        self.c_pipe.send(Command(Verb.GET, Noun.VAL_CURRENT_SPEED))
        if not self.r_pipe.poll(2):
            self.fail()
        result = self.r_pipe.recv()
        self.assertEqual(Noun.VAL_CURRENT_SPEED, result.noun)
        self.assertTrue(result.value == 20)
        self.c_pipe.send(Command(Verb.STOP, 0))
        self.c_pipe.send(Command(Verb.QUIT, 0))
        self.process.join()

    def test_get_value_acceleration(self):
        print("Test get_value() ACCELERATION")
        self.process.start()
        self.c_pipe.send(Command(Verb.ACCELERATION, 1234))
        self.c_pipe.send(Command(Verb.GET, Noun.VAL_ACCELERATION))
        if not self.r_pipe.poll(1):
            self.fail()
        result = self.r_pipe.recv()
        self.assertEqual(Noun.VAL_ACCELERATION, result.noun)
        self.assertEqual(1234, result.value)
        self.c_pipe.send(Command(Verb.QUIT, 0))
        self.process.join()

    def test_get_value_deceleration(self):
        print("Test get_value() DECELERATION")
        self.process.start()
        self.c_pipe.send(Command(Verb.DECELERATION, 2345))
        self.c_pipe.send(Command(Verb.GET, Noun.VAL_DECELERATION))
        if not self.r_pipe.poll(1):
            self.fail()
        result = self.r_pipe.recv()
        self.assertEqual(Noun.VAL_DECELERATION, result.noun)
        self.assertEqual(2345, result.value)
        self.c_pipe.send(Command(Verb.QUIT, 0))
        self.process.join()

    def test_get_value_target_position(self):
        print("Test get_value() TARGET_POSITION")
        self.process.start()
        self.c_pipe.send(Command(Verb.MOVETO, 10))
        self.c_pipe.send(Command(Verb.GET, Noun.VAL_TARGET_POSITION))
        if not self.r_pipe.poll(2):
            self.fail()
        result = self.r_pipe.recv()
        self.assertEqual(Noun.VAL_TARGET_POSITION, result.noun)
        self.assertEqual(10, result.value)
        self.c_pipe.send(Command(Verb.STOP, 0))
        self.c_pipe.send(Command(Verb.QUIT, 0))
        self.process.join()

    def test_get_value_current_position(self):
        print("Test get_value() CURRENT_POSITION")
        self.process.start()
        self.c_pipe.send(Command(Verb.MOVETO, 100))
        time.sleep(0.1)
        self.c_pipe.send(Command(Verb.GET, Noun.VAL_CURRENT_POSITION))
        if not self.r_pipe.poll(2):
            self.fail()
        result = self.r_pipe.recv()
        self.assertEqual(Noun.VAL_CURRENT_POSITION, result.noun)
        self.assertTrue(0 < result.value < 100)
        self.c_pipe.send(Command(Verb.STOP, 0))
        self.c_pipe.send(Command(Verb.QUIT, 0))
        self.process.join()

    def test_get_value_full_steps_per_rev(self):
        print("Test get_value() FULL_STEPS_PER_REV")
        self.process.start()

        # Test Setter and Getter
        self.c_pipe.send(Command(Verb.FULL_STEPS_PER_REV, 123))
        self.c_pipe.send(Command(Verb.GET, Noun.VAL_FULL_STEPS_PER_REV))
        if not self.r_pipe.poll(2):
            self.fail()
        result = self.r_pipe.recv()
        self.assertEqual(Noun.VAL_FULL_STEPS_PER_REV, result.noun)
        self.assertEqual(123, result.value)
        self.c_pipe.send(Command(Verb.STOP, 0))
        self.c_pipe.send(Command(Verb.QUIT, 0))
        self.process.join()

        # Check that rotational moves pick up the new value
        self.process.steps_per_rev(1000)
        self.process.moveto_deg(360)  # one rotation CW
        self.assertEqual(1000, self.process.target_position)

        self.process.zero()
        self.process.steps_per_rev(2048)
        self.process.microsteps = 2
        self.process.move_deg(-360)
        self.assertEqual(-4096, self.process.target_position)
