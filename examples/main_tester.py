#!/usr/bin/python3
'''
Created on 11.06.2020

@author: thoma
'''

import sys
import time

import advpistepper as apis
import pigpio



def main(argv):
    """just some debug / test code"""
    if len(argv) > 1:
        steps = int(argv[1])
    else:
        steps = 1000
    pi = pigpio.pi()

    pi.set_mode(17, pigpio.OUTPUT)
    pi.write(17, 0)

    drv_28byj48 = apis.Driver28BYJ48(pink=23, orange=25, yellow=24, blue=22)

    stepper = apis.AdvPiStepper(drv_28byj48)

    pi.write(17, 1)

    stepper.microsteps = 1

#    stepper.move(500, 2000, block=True)

    stepper.target_speed = 1700
    stepper.run(1)
    time.sleep(5)
    stepper.stop(True)

    time.sleep(0.1)
    stepper.release()
    pi.write(17, 0)
    quit(0)


#    while True:
#        pass
#
#    for i in range(10):
#        time.sleep(1.0)
#        stepper.target_speed = 100+(i * 100)

    stepper.stop(True)

#    stepper.move(1000, 1, True)

    stepper.release()


if __name__ == '__main__':
    main(sys.argv)
