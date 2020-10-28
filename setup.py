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

import io
import os
import sys
import errno
import setuptools

if sys.version_info[0] == 3:
    if not sys.version_info >= (3, 7):
        raise ValueError('This package requires Python 3.7 or above')
else:
    raise ValueError('Unsupported version of Python')

HERE = os.path.abspath(os.path.dirname(__file__))

__project__ = 'AdvPiStepper'
__version__ = '0.9.0.dev2'
__author__ = 'Thomas Holland'
__author_email__ = 'thomas@innot.de'
__url__ = 'https://github.com/innot/advpistepper'
__platforms__ = 'raspberrypi'
__docs__ = 'Python stepper motor controller/driver for the Raspberry Pi using pigpio'
__license__ = 'MIT'

__classifiers__ = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Education",
    "Intended Audience :: Developers",
    "Topic :: Education",
    "Topic :: System :: Hardware :: Hardware Drivers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.7",
    #    "Programming Language :: Python :: Implementation :: PyPy",
]

__project_urls__ = {
    'Documentation': 'https://advpistepper.readthedocs.io/',
    'Source': 'https://github.com/innot/AdvPiStepper',
    'Tracker': 'https://github.com/innot/AdvPiStepper/issues',
}

__keywords__ = [
    'raspberrypi',
    'stepper',
    'motor'
    '28byj-48',
    'pigpio',
]

__requires__ = [
    'pigpio>=1.78'
]

__extra_requires__ = {
    'doc': ['sphinx'],
    'test': ['pytest', 'coverage', 'mock'],
}

__entry_points__ = {
    'console_scripts': [
        'advpistepper = advpistepper.stepper:main',
    ]
}


def main():
    with open(os.path.join(HERE, "README.rst"), "r") as fh:
        __long_description__ = fh.read()

    setuptools.setup(
        name=__project__,
        version=__version__,
        description=__doc__,
        long_description=__long_description__,
        long_description_content_type="text/x-rst",
        classifiers=__classifiers__,
        author=__author__,
        author_email=__author_email__,
        url=__url__,
        project_urls=__project_urls__,
        license=__license__,
        keywords=__keywords__,
        packages=setuptools.find_packages(),
        include_package_data=True,
        platforms=__platforms__,
        install_requires=__requires__,
        python_requires='>=3.7',
        extras_require=__extra_requires__,
        entry_points=__entry_points__,
    )


if __name__ == '__main__':
    print("Building AdvPiStepper")
    main()
