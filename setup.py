#  Copyright (c) 2020 Thomas Holland (thomas@innot.de)
#  All rights reserved.
#
#  This code is licensed under the MIT License.
#
#  Refer to the LICENSE file which is part of the AdvPiStepper distribution or
#  to https://opensource.org/licenses/MIT for a text of the license.
#
#
#
#  This code is licensed under the MIT License.
#
#  Refer to the LICENSE file which is part of the AdvPiStepper distribution or
#  to https://opensource.org/licenses/MIT for a text of the license.
#
#

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name='AdvPiStepper',
    version='0.9.0.dev1',
    packages=setuptools.find_packages(),
    install_requires=['pigpio'],
    url='https://github.com/innot/AdvPiStepper',
    license='MIT',
    author='Thomas Holland',
    author_email='thomas@innot.de',
    description='Python stepper motor controller/driver for the Raspberry Pi using pigpio',
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.7",
        "Topic :: System :: Hardware :: Hardware Drivers"
    ],
    python_requires='>=3.7',
)
