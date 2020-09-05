#  Copyright (c) 2020 Thomas Holland (thomas@innot.de)
#  All rights reserved.
#
#  This code is licensed under the MIT License.
#
#  Refer to the LICENSE file which is part of the AdvPiStepper distribution or
#  to https://opensource.org/licenses/MIT for a text of the license.
#
#
import unittest

import advpistepper as apis


class MyTestCase(unittest.TestCase):
    apis = None

    def setUp(self):
        self.apis = apis.AdvPiStepper()

    def tearDown(self) -> None:
        self.apis.close()

    def test_target_speed(self):
        print("test target_speed")

        test = (1234, 1.0, 0.1, 1000000)
        for v in test:
            self.apis.target_speed = v
            self.assertEqual(v, self.apis.target_speed)

        with self.assertRaises(ValueError):
            self.apis.target_speed = 0
            self.apis.target_speed = -1

        # test speed change during a run
        self.apis.run(apis.CW, 1000)
        self.assertEqual(1000, self.apis.target_speed)
        self.apis.stop()
        print("test target_speed completed")

    def test_current_position(self):
        print("test current_position")
        self.apis.move(100, block=True)
        self.assertEqual(100, self.apis.current_position)
        self.apis.move(100, block=True)
        self.assertEqual(200, self.apis.current_position)
        self.apis.move(-300, block=True)
        self.assertEqual(-100, self.apis.current_position)
        self.apis.zero()
        self.assertEqual(0, self.apis.current_position)
        self.apis.close()

    def test_move(self):
        print("test move")
        self.apis.move(50, block=True)
        self.assertEqual(50, self.apis.target_position, "wrong target_position")
        self.assertEqual(50, self.apis.current_position, "wrong current_position")

        self.apis.move(100, block=True)
        self.assertEqual(150, self.apis.target_position, "wrong target_position")
        self.assertEqual(150, self.apis.current_position, "wrong current_position")

        self.apis.move(-200, block=True)
        self.assertEqual(-50, self.apis.target_position, "wrong target_position")
        self.assertEqual(-50, self.apis.current_position, "wrong current_position")

        self.apis.close()
        print("test move completed")

    def test_move_to(self):
        print("test move_to")
        self.apis.move_to(100, block=True)
        self.assertEqual(100, self.apis.target_position, "wrong target_position")
        self.assertEqual(100, self.apis.current_position, "wrong current_position")

        self.apis.move_to(50, block=True)
        self.assertEqual(50, self.apis.target_position, "wrong target_position")
        self.assertEqual(50, self.apis.current_position, "wrong current_position")

        self.apis.move_to(-50, block=True)
        self.assertEqual(-50, self.apis.target_position, "wrong target_position")
        self.assertEqual(-50, self.apis.current_position, "wrong current_position")

        self.apis.move_to(0, block=True)
        self.assertEqual(0, self.apis.target_position, "wrong target_position")
        self.assertEqual(0, self.apis.current_position, "wrong current_position")


    def test_close(self):
        print("test close")
        self.apis.close()
        self.assertFalse(self.apis.process.is_alive())

        obj = apis.AdvPiStepper()
        del obj  # should not throw any errors.
        print("test close completed")


if __name__ == '__main__':
    unittest.main()
