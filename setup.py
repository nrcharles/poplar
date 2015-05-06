# Copyright (C) 2015 Nathan Charles
#
# This program is free software. See terms in LICENSE file.
"""install"""
from __future__ import absolute_import
import os
from setuptools import setup, find_packages
import datetime

NOW = datetime.datetime.now()
MAJOR = 0

def read(fname):
    """README helper function"""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="poplar",
    version="%s.%s.%s.%s" % (MAJOR, NOW.month, NOW.day, NOW.hour),
    author="Nathan Charles",
    author_email="ncharles@gmail.com",
    # python framework to optimize microgrid sizing using multi-criteria decision analysis
    description=("multi-criteria microgrid optimization framework"),
    license="AGPL",
    keywords="Photovoltaic PV Solar microgrid off-grid",
    url="https://github.com/nrcharles/poplar",
    packages=find_packages(),
    long_description=read('README.rst'),
    install_requires=['geopy', 'caelum', 'solpy'],
    package_data={'': ['*.csv','*.txt','*.rst']},
    test_suite='tests.unit',
    classifiers=[
        "Development Status :: 4 - Beta",
        ("License :: OSI Approved :: GNU Affero General Public License v3 "
         "or later (AGPLv3+)"),
    ],
)
