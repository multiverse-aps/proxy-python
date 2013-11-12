# -*- coding: utf-8 -*-
r"""
proxy-python
---

A proxy python client.
"""

import sys

from setuptools import setup
try:
    import multiprocessing
except ImportError:
    pass

def run_setup(with_binary):
    features = {}

    setup(
        name='proxy-python',
        version='0.3.1',
        license='MIT',
        url='https://github.com/simonz05/proxy-python/',
        author='Simon Zimmermann',
        author_email='simon@insmo.com',
        description='A proxy Python client',
        long_description=__doc__,
        keywords="proxy",
        platforms='any',
        packages=['proxy'],
        features=features,
        install_requires=['requests'],
        test_suite="nose.collector",
        tests_require=['nose'],
        classifiers=[
            "Development Status :: 2 - Pre-Alpha",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: POSIX",
            "Programming Language :: Python",
            "Topic :: Software Development",
            "Topic :: Software Development :: Libraries",
        ],
    )

def echo(msg=''):
    sys.stdout.write(msg + '\n')

run_setup(True)
