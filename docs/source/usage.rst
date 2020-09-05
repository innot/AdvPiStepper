Usage
-----

Installation
............

AdvPiStepper is very simple to use.

.. highlight:: python
   :linenothreshold: 5

.. code-block:: python

   import advpistepper

   driver = advpistepper.Driver28BYJ48(pink=23, orange=25, yellow=24, blue=22)
   stepper = advpistepper.AdvPiStepper(driver)
   stepper.move(100)


