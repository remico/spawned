#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  This file is part of "Spawned" project
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

"""Run bash commands in a chroot environment"""

from pathlib import Path

from .spawned import SpawnedSU, Spawned, _TMP
from . import logger as log

__author__ = "Roman Gladyshev"
__email__ = "remicollab@gmail.com"
__copyright__ = "Copyright (c) 2020, REMICO"
__license__ = "LGPLv3+"

__all__ = ['Chroot', 'ChrootContext']


@log.tagged("[Chroot]", log.ok_blue_s)
def _p(*text): return text


class Chroot:
    def __init__(self, root):
        self.chroot_tmp = Path(root, str(_TMP)[1:])  # slice leading '/' to be able to concatenate
        self.chroot_cmd = f'chroot {root} bash "{{}}"'

    def _before(self):
        SpawnedSU.do(f"mkdir -p {self.chroot_tmp} && mount --bind {_TMP} {self.chroot_tmp}")

    def _after(self):
        SpawnedSU.do(f"umount {self.chroot_tmp} && rm -r {self.chroot_tmp}")

    def do(self, script):
        try:
            self._before()
            SpawnedSU.do_script(script, bg=False, cmd=self.chroot_cmd)
        finally:
            self._after()


class ChrootContext(Chroot):
    def __enter__(self):
        self._before()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._after()

    def do(self, script) -> Spawned:
        """Run script and wait until it ends"""
        return SpawnedSU.do_script(script, async_=False, bg=False, cmd=self.chroot_cmd)

    def doi(self, script) -> Spawned:
        """Run script and continue execution.
        Returned value can be used as context manager.
        """
        return SpawnedSU.do_script(script, async_=True, bg=False, cmd=self.chroot_cmd)
