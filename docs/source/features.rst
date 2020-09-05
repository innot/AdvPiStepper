Features
--------

* Uses acceleration and deceleration ramps.
* Fairly tight timing up to approx. 1500 steps per second (on Raspberry Pi 4) [#]_.
* Complete API for relative and absolute moves, rotations and continuous running.
* Runs in the background. Motor movements can be blocking or non-blocking.
* Support for microstepping (depending on the driver).
* Support for unipolar stepper motors

    - Like the cheap 28BYJ48 motor

* {TODO} Support for Bipolar stepper drivers / dual H-Bridges like the

    - L293(D)
    - DRV8833

* {TODO} Support for Step/Direction controllers like

    - A4988
    - DRV8825
    - STSPIN220 / 820

* Other drivers should be easy to implement
* Licensed under the very permissive MIT license.

.. [#] At high step rates occasional stutters may occur when some
    Python / Linux background tasks run.