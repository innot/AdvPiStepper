Usage
-----

   "A journey of a thousand miles begins with a single step"
   -- Laozi

Installation
............

AdvPiStepper can be

.. code-block:: bash

   $ pip install advpistepper

Usage
.....
AdvPiStepper is very simple to use. Here is a small example
using the :mod:`28BYJ-48 <advpistepper.driver_unipolar_28byj48>` driver:

.. highlight:: python
   :linenothreshold: 5

.. code-block:: python

   import advpistepper

   driver = advpistepper.Driver28BYJ48(pink=23, orange=25, yellow=24, blue=22)
   stepper = advpistepper.AdvPiStepper(driver)
   stepper.move(100)


Refer to :mod:`the API <advpistepper.stepper>`

Tuning
......

To get the best performance from AdvPiStepper there should be as few
background processes running as possible. For expample, on the AdvPiStepper
development system (Raspi 4) the Desktop process does interfere with the
AdvPiStepper process about every 500ms causing step delays of a few milliseconds,
enough to cause late step pulses at high speeds (>500 steps per second)

If AdvPiStepper is called with root privileges (sudo) it will
decrease the niceness of the backend process to -10. This improves the
timing at high speeds somewhat due to less interference by normal
user processes.
