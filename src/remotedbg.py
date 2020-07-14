'''
Created on 11.06.2020

@author: thoma
'''

import pigpio

from advpistepper.stepper import AdvPiStepper
from advpistepper.driver_unipolar_28BYJ48 import Driver28BYJ48

import sys;sys.path.append(r'C:\java\eclipse\eclipse-pde\plugins\org.python.pydev.core_7.6.0.202006041357\pysrc')
import pydevd;pydevd.settrace("toms-spectre")

if __name__ == '__main__':
    drv_28byj48 = Driver28BYJ48(pink=18, orange=14, yellow=15, blue=17)
    
    pi = pigpio.pi("raspberrypi")
    
    stepper = AdvPiStepper(pi, drv_28byj48)
    
    stepper.engage()
    
    stepper.move(+500)
    
    stepper.disengage()
    
    quit()
    
