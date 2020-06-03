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

from .spawned import SpawnedSU, Spawned
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
        chroot_path = "/chroot.fifo"
        real_path = f"{root}{chroot_path}"

        try:
            SpawnedSU.do(f"touch {real_path}; chmod 777 {real_path}")
            Path(real_path).write_text(script.strip())
            cmd = f'chroot {root} bash "{chroot_path}"'

            # debugging output
            if Spawned._log_commands:
                _p("@ FIFO:", Path(real_path).read_text())

            t = Spawned(cmd, timeout=Spawned.TO_INFINITE, sudo=True)
            t.waitfor(Spawned.TASK_END)
        finally:
            SpawnedSU.do(f"rm {real_path}")
