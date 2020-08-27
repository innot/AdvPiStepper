 .. AdvPiStepper documentation master file, created by
   sphinx-quickstart on Tue Aug 25 22:17:28 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to AdvPiStepper's documentation!
========================================

AdvPiStepper is a driver for all kinds of stepper motors, written in Python for the Raspberry Pi, using the pigpio library.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   features
   requirements

.. warning::

   This program is not finished. It was uploaded to GitHub as a backup.
   Feel free to look at the source code and give feedback, but do not expect it to work
   in any shape or form.

.. include:: features.rst




Usage
-----


.. highlight:: python
   :linenothreshold: 5


.. code-block:: python

   import advpistepper

   driver = advpistepper.Driver28BYJ48(pink=23, orange=25, yellow=24, blue=22)
   stepper = advpistepper.AdvPiStepper(driver)
   stepper.move(100)


Theory of Operation
-------------------

History
-------
AdvPiStepper was started for a Raspberry Pi project where I needed to move a stepper motor
for 400 +/- a few steps. I wanted acceleration and deceleration ramps because
an early Arduino based prototype had them. As I could not find any suitable RPi library
I started this programm, which quickly spiraled out of control and became this
multipurpose stepper motor controller.

V0.9 Work in Progress - Not officially released



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
