#  Copyright (c) 2020 Thomas Holland (thomas@innot.de)
#  All rights reserved.
#
#  This code is licensed under the MIT License.
#
#  Refer to the LICENSE file which is part of the AdvPiStepper distribution or
#  to https://opensource.org/licenses/MIT for a text of the license.
#
#

import multiprocessing
import time
import unittest

import pigpio

import advpistepper
import advpistepper as stepper


class ConstantDelayDriver(advpistepper.driver_base.DriverBase):

    def __init__(self, delay):
        self.delay = int(delay)
        super().__init__()

    def perform_step(self, delay: int) -> list:
        return [pigpio.pulse(0, 0, self.delay)]


class TestTimings(unittest.TestCase):

    def test_max_speed(self):
        tolerance = 10  # percent
        speed = 100  # Hz
        steps = 500  # steps per iteration

        while True:
            driver = ConstantDelayDriver(1000000 / speed)

            c_pipe_remote, c_pipe = multiprocessing.Pipe()
            r_pipe, r_pipe_remote = multiprocessing.Pipe()
            idle_event = multiprocessing.Event()

            process = stepper.StepperProcess(c_pipe_remote, r_pipe_remote, idle_event, driver)
            process.connect_pigpio()

            t0 = time.perf_counter_ns()
            process.move(steps)
            process.busy_loop()
            t1 = time.perf_counter_ns()
            dt = (t1 - t0) / 1000

            target = (1000000 / speed) * steps
            diff_abs = int(dt - target)
            diff_percent = (diff_abs / target) * 100

            print(
                f"{steps} Steps @ {speed}Hz should take {target} us, took: {dt} us. Diff {diff_abs}us = {diff_percent}%")

            process.close()

            if diff_percent < tolerance:
                speed += 100
            else:
                break


if __name__ == '__main__':
    unittest.main()
