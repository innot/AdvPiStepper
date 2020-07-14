'''
Created on 11.06.2020

@author: thoma
'''

import sys
import pigpio

from advpistepper.stepper import AdvPiStepper
from advpistepper.driver_unipolar_28byj48 import Driver28BYJ48


def main(argv):
    """just some debug / test code"""
    if len(argv) > 1:
        steps = int(argv[1])
    else:
        steps = -10

    drv_28byj48 = Driver28BYJ48(pink=18, orange=14, yellow=15, blue=17)

    pi_drv = pigpio.pi()

    stepper = AdvPiStepper(pi_drv, drv_28byj48)

    stepper.engage()

    stepper.move(steps)
    
#    stepper.move(3)

 #   stepper.move(3)

    stepper.disengage()


if __name__ == '__main__':
    main(sys.argv)
