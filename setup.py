#!/usr/bin/env python

import os
from setuptools import setup
from setuptools.command.test import test


def root_dir():
    rd = os.path.dirname(__file__)
    if rd:
        return rd
    return '.'


class pytest_test(test):
    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        pytest.main([])


setup_args = dict(
    name='dynpool',
    version='1.0',
    url='https://tabo.pe/projects/dynpool/',
    author='Gustavo Picon',
    author_email='tabo@tabo.pe',
    license='Apache License 2.0',
    py_modules=['dynpool'],
    description='Python library that handles the growing and shrinking '
                'of a pool of resources depending on usage patterns.',
    long_description=open(root_dir() + '/README').read(),
    cmdclass={'test': pytest_test},
    tests_require=['pytest', 'Mock'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries'])

if __name__ == '__main__':
    setup(**setup_args)
