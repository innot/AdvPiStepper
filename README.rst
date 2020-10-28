About
=====
AdvPiStepper is a driver for all kinds of stepper motors, written in Python for the Raspberry Pi, using the pigpio library.

.. warning::
    this program is not finished. It was uploaded to GitHub as a backup.
    Feel free to look at the source code and give feedback, but do not expect it to work
    in any shape or form.

.. code:: python

   import advpistepper

   driver = advpistepper.DriverStepDirGeneric(step_pin=22, dir_pin=23)
   stepper = advpistepper.AdvPiStepper(driver)
   stepper.move(100)


This small example will move a stepper motor whose controller step pin
is connected to pin 22 of the raspberry pi and whose direction pin is
connected to pin 23.

Features
========
* Uses acceleration and deceleration ramps.
* Fairly tight timing up to approx. 1500 steps per second (on Raspberry Pi 4) [#]_.
* Complete API for relative and absolute moves, rotations and continuous running.
* Runs in the background. Motor movements can be blocking or non-blocking.
* Support for microstepping (depending on the driver).
* Support for any unipolar stepper motors, like:
    - 28BYJ-48 (very cheap geared stepper)
* {TODO} Support for Bipolar stepper drivers / dual H-Bridges like the
    - L293(D)
    - DRV8833
* {TODO} Support for Step/Direction controllers like
    - A4988
    - DRV8825
    - STSPIN220 / 820
* Other drivers should be easy to implement
* Licensed under the very permissive MIT license.
* 100% Python, no dependencies except pigpio.

.. [#] At high step rates occasional stutters may occur when some
    Python / Linux background tasks run.

Uses
----

AdvPiStepper is suitable for

* Python projects that need to accuratly control a single stepper motor at reasonable speeds.
* Stepper motor experiments and prototyping.

It is _not_ suitable for

* multi-axis stepper motor projects
* high speeds (> 1500 steps per second)


Caveats
-------

* Currently no support for multiple motors. Single motor only.

* 100% Python, therefore no realtime performance - jitter and stutters may occur.

Requirements
============

AdvPiStepper has only a single dependency:

pigpio V76 or higher
--------------------
AdvPiStepper requires the `pigpio <http://abyz.me.uk/rpi/pigpio/>`__
library to work. If `Remote GPIO <https://gpiozero.readthedocs.io/en/stable/remote_gpio.html>`__
has been enabled in the Raspberry Pi configuration tool, then the pigpio daemon should already
be installed and running.
Run the following to check if pigpio daemon is installed and its version number:

.. code:: bash

   $ pigpiod -v
   76

If either pigpio is not installed or has a version smaller than 76 (the minimum
version required by AdvPiStepper), then refer to the pigpio
`download & install <http://abyz.me.uk/rpi/pigpio/download.html>`__ page on how to
install pigpio.

Python 3.7 or higher
--------------------
AdvPiStepper is developed and tested with Python 3.7. Older Python version may or may not work.

Installation
============
If the requirements are met, then a simple

.. code:: bash

    $ pip import advpistepper

will install the AdvPiStepper module.

Documentation
=============
Comprehensive documentation is available at https://advpistepper.readthedocs.io/.

