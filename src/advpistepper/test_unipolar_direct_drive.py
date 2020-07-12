'''
Created on 08.06.2020

@author: thoma
'''
import unittest

from pi_accel_stepper.unipolar_driver import UnipolarDriver


class TestUnipolarDriver(unittest.TestCase):
    
    stepper = 0

    def setUp(self):
        self.driver = UnipolarDriver()

    def tearDown(self):
        pass

    def test_set_get_microsteps(self):
        self.driver.set_microsteps(1)
        self.assertEqual(1, self.driver.get_microsteps())

        self.driver.set_microsteps(2)
        self.assertEqual(2, self.driver.get_microsteps())
        
        with self.assertRaises(ValueError):
            self.driver.set_microsteps(0)
            self.driver.set_microsteps(3)

    def test_set_get_maxpps(self):
        self.driver.set_max_pps(1)
        self.assertEqual(1, self.driver.get_max_pps())

        self.driver.set_max_pps(1000)
        self.assertEqual(1000, self.driver.get_max_pps())
        
        with self.assertRaises(ValueError):
            self.driver.set_max_pps(0)
            self.driver.set_max_pps(-1)
            
    def testGetSetPins(self):
        self.driver.set_pins(a1=10, a2=11, b1=12, b2=13)
        result = self.driver.get_pins()
        self.assertEqual(result, [10, 11, 12, 13])
        
        # test immutable
        result[0] = 99
        result2 = self.driver.get_pins()
        self.assertNotEqual(result2, result)
            
    def testGetWaveStepCW(self):
        for i in range(0, 17):
            wave = self.driver.get_wave_step_forward()
            print(f"{i}. ({wave})")
            
    def testGetWaveStepCCW(self):
        for i in range(0, 17):
            wave = self.driver.get_wave_step_backward()
            print(f"{i}. ({wave})")


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
