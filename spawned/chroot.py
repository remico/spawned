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

__author__ = "Roman Gladyshev"
__email__ = "remicollab@gmail.com"
__copyright__ = "Copyright (c) 2020, REMICO"
__license__ = "LGPLv3+"

__all__ = ['Chroot']


class Chroot:
    @staticmethod
    def do(root, script):
        file_name = "/chroot.fifo"
        fifo_path = f"{root}{file_name}"

        try:
            SpawnedSU.do(f"touch {fifo_path}; chmod 777 {fifo_path}")
            Path(fifo_path).write_text(script.strip())
            cmd = f'chroot {root} bash "{file_name}"'
            t = Spawned(cmd, timeout=Spawned.TO_INFINITE, sudo=True)
            t.waitfor(Spawned.TASK_END)
        finally:
            SpawnedSU.do(f"rm {fifo_path}")
