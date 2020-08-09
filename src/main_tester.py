'''
Created on 11.06.2020

@author: thoma
'''

import sys
import pigpio
import time

from advpistepper.stepper import AdvPiStepper
from advpistepper.driver_unipolar_28byj48 import Driver28BYJ48


def main(argv):
    """just some debug / test code"""
    if len(argv) > 1:
        steps = int(argv[1])
    else:
        steps = 1000

    drv_28byj48 = Driver28BYJ48(pink=17, orange=22, yellow=27, blue=4)

    stepper = AdvPiStepper(drv_28byj48)

    stepper.microsteps = 2

    stepper.engage()

    stepper.target_speed = 100

    stepper.run(1)

    for i in range(15):
        time.sleep(1.0)
        stepper.target_speed = 100+(i * 100)

    stepper.stop(True)

#    stepper.move(1000, 1, True)

    stepper.release()


if __name__ == '__main__':
    main(sys.argv)
