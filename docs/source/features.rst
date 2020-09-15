Features
--------

   "Here comes the Hotstepper"
   -- Ini Kamoze

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

Caveats
.......

* Currently no support for multiple motors. Single motor only.

* 100% Python, therefore no realtime performance - jitter and stutters may occur.
