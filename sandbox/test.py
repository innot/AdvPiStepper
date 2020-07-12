#!/usr/bin/python

import sys
import pydevd

sys.path.append(r'/home/pi/dev/accelstepper')

pydevd.settrace('192.168.178.20') # replace IP with address of Eclipse host machine

i = 3
p = 'Hello!' * i
print(p)
