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

import advpistepper.stepper


class MyTestCase(unittest.TestCase):
    apis = None

    def setUp(self):
        pass

    def test_target_speed(self):
        apis = advpistepper.AdvPiStepper()
        test = (1234, 1.0, 0.1, 1000000)
        for v in test:
            apis.target_speed = v
            self.assertEqual(v, apis.target_speed)

        with self.assertRaises(ValueError):
            apis.target_speed = 0
            apis.target_speed = -1

        # test speed change during a run
        apis.run(1000)
        self.assertEqual(1000, apis.target_speed)


if __name__ == '__main__':
    unittest.main()
