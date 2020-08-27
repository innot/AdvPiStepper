Requirements
------------

AdvPiStepper uses the `pigpio <http://abyz.me.uk/rpi/pigpio/>`__
library to access the Raspberry Pi GPIO pins.
It requires at least V76 of the library, which at the
time of writing has not yet been uploaded to
`PyPI.org <https://pypi.org/project/pigpio/>`__
and therefore has to be
`installed manually <http://abyz.me.uk/rpi/pigpio/download.html>`__.

A multicore Raspberry Pi (Model 2/3/4) is recommended so that the
stepper engine with its critical timings can run on a seperate core.
Single Core Pi Models (or heavy load on more than one core) will
have timing jitter - neither Linux nor Python is really suited
for these realtime uses.
