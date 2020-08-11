'''
Created on 11.06.2020

@author: thoma
'''

import sys
import time

import advpistepper as apis


def main(argv):
    """just some debug / test code"""
    if len(argv) > 1:
        steps = int(argv[1])
    else:
        steps = 1000

    drv_28byj48 = apis.Driver28BYJ48(pink=23, orange=25, yellow=24, blue=22)

    stepper = apis.AdvPiStepper(drv_28byj48)

    stepper.microsteps = 2

    stepper.engage()
    stepper.move(100, 100)

    time.sleep(2)

    stepper.release()

    quit(0)

    stepper.target_speed = 100

    stepper.run(1)

    for i in range(10):
        time.sleep(1.0)
        stepper.target_speed = 100+(i * 100)

    stepper.stop(True)

#    stepper.move(1000, 1, True)

    stepper.release()


if __name__ == '__main__':
    main(sys.argv)
