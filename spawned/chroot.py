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

from .spawned import SpawnedSU, _TMP
from . import logger as log

__author__ = "Roman Gladyshev"
__email__ = "remicollab@gmail.com"
__copyright__ = "Copyright (c) 2020, REMICO"
__license__ = "LGPLv3+"

__all__ = ['Chroot']


@log.tagged("[Chroot]", log.ok_blue_s)
def _p(*text): return text


class Chroot:
    @staticmethod
    def do(root, script):
        chroot_tmp = Path(root, str(_TMP)[1:])  # slice leading '/' to be able to concatenate
        chroot_cmd = f'chroot {root} bash "{{}}"'

        try:
            SpawnedSU.do(f"mkdir -p {chroot_tmp} && mount --bind {_TMP} {chroot_tmp}")
            SpawnedSU.do_script(script, timeout_s=SpawnedSU.TO_INFINITE, bg=False, cmd=chroot_cmd)
        finally:
            SpawnedSU.do(f"umount {chroot_tmp} && rm -r {chroot_tmp}")
