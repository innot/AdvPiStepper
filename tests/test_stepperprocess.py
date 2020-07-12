from unittest import TestCase

from advpistepper.stepper import *


class TestStepperProcess(TestCase):
    def setUp(self) -> None:
        driver = DriverBase()
        pi = pigpio.pi("raspberrypi")

        c_pipe_remote, self.c_pipe = multiprocessing.Pipe()
        self.r_pipe, r_pipe_remote = multiprocessing.Pipe()

        self.process = StepperProcess(c_pipe_remote, r_pipe_remote, driver, pi)

    def test_speed(self):
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
        self.process.deceleration(1234)
        self.assertEqual(self.process.decel, 1234)

    def test_move(self):
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
        pass

    def test_stop(self):
        pass

    def test_hardstop(self):
        pass
