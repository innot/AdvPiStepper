Usage
-----

   "A journey of a thousand miles begins with a single step"
   -- Laozi

Installation
............

.. code-block:: bash
pip3 install advpistepper


Usage
.....
AdvPiStepper is very simple to use.

.. highlight:: python
   :linenothreshold: 5

.. code-block:: python

   import advpistepper

   driver = advpistepper.Driver28BYJ48(pink=23, orange=25, yellow=24, blue=22)
   stepper = advpistepper.AdvPiStepper(driver)
   stepper.move(100)


Refer to :mod:`the API <advpistepper.stepper>`

If AdvPiStepper is called with root privileges (sudo) it will
decrease the niceness of the backend process to -10. This improves the
timing at high speeds somewhat due to less interference by all normal
user processes.

