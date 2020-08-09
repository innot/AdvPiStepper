# AdvPiStepper
AdvPiStepper is a driver for all kinds of stepper motors, written in Python for the Raspberry Pi, using the pigpio library.

**ATTENTION** this program is not finished. It was uploaded to GitHub as a backup.
Feel free to look at the source code and give feedback, but do not expect it to work
in any shape or form.

## Features
* Uses acceleration and deceleration ramps.
* Fairly tight timing up to approx. 3000 steps per second (on Raspberry Pi 4).
* Complete API for relative and absolute moves, rotations and continuous running.
* Runs in the background. Motor movements can be blocking or non-blocking.
* Support for microstepping (depending on the driver).
* Support for unipolar stepper motors
    * Like the cheap 28BYJ48 motor
* {TODO} Support for Bipolar stepper drivers / dual H-Bridges like the
    * L293(D)
    * DRV8833 
* {TODO} Support for Step/Direction controllers like
    * A4988 
    * DRV8825
    * STSPIN220 / 820
* Other drivers should be easy to implement
* Licensed under the very permissive MIT license.

## Requirements
AdvPiStepper uses the [pigpio](http://abyz.me.uk/rpi/pigpio/) library to access the Raspberry Pi GPIO pins.
It requires at least V76 of the library, which at the time of writing has not yet been uploaded to the PyPI archive and
therefore has to be [installed manually](http://abyz.me.uk/rpi/pigpio/download.html).

## Usage
To use the AdvPiStepper {TODO}

## Theory of Operation

## History
V0.1 Work in Progress - Not officially released

