#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2020, REMICO
#
#  The software is provided "as is", without warranty of any kind, express or
#  implied, including but not limited to the warranties of merchantability,
#  fitness for a particular purpose and non-infringement. In no event shall the
#  authors or copyright holders be liable for any claim, damages or other
#  liability, whether in an action of contract, tort or otherwise, arising from,
#  out of or in connection with the software or the use or other dealings in the
#  software.

import setuptools
from spawned.spawned import Spawned

__author__ = "Roman Gladyshev"
__email__ = "remicollab@gmail.com"
__copyright__ = "Copyright (c) 2020, REMICO"
__license__ = "LGPLv3+"


with open("README.md") as f:
    long_description = f.read()


# make the distribution platform dependent
try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
    class bdist_wheel(_bdist_wheel):
        def finalize_options(self):
            _bdist_wheel.finalize_options(self)
            self.root_is_pure = False
except ImportError:
    bdist_wheel = None


setuptools.setup(
    name="spawned",
    version=Spawned.do("cat **/VERSION"),
    author="remico",
    author_email="remicollab@gmail.com",
    description="A simple python module for dealing with sub-processes",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/remico/spawned",
    packages=setuptools.find_packages(exclude=['sndbx', 'test', 'tests']),
    package_data={'': ['VERSION']},
    py_modules=[],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: POSIX :: Linux",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Shells",
    ],
    python_requires='>=3.8',
    install_requires=['pexpect'],
    license='LGPLv3+',
    platforms=['POSIX'],
    cmdclass={'bdist_wheel': bdist_wheel},
)
