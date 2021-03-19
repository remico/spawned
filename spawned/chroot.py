#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  This file is part of "Spawned" project
#
#  Author: Roman Gladyshev <remicollab@gmail.com>
#  License: GNU Lesser General Public License v3.0 or later
#
#  SPDX-License-Identifier: LGPL-3.0+
#  License text is available in the LICENSE file and online:
#  http://www.gnu.org/licenses/lgpl-3.0-standalone.html
#
#  Copyright (c) 2020 remico

"""Run bash commands in a chroot environment"""

from pathlib import Path

from .spawned import SpawnedSU, Spawned, _TMP, MODULE_PFX, onExit
from . import logger as log

__all__ = ['Chroot', 'ChrootContext']


@log.tagged("[Chroot]", log.ok_blue_s)
def _p(*text): return text


class Chroot:
    def __init__(self, root):
        self.root = root
        self.chroot_tmp = Path(root, str(_TMP)[1:])  # slice leading '/' to be able to concatenate

    def chroot_cmd(self, user=None):
        user_opt = f"--userspec={user}:{user}" if user else ""
        return f'chroot {user_opt} {self.root} bash "{{}}"'

    def _before(self):
        SpawnedSU.do(f"mkdir -p {self.chroot_tmp} && mount --bind {_TMP} {self.chroot_tmp}")

    def _after(self):
        SpawnedSU.do(f"umount {self.chroot_tmp} && rm -r {self.chroot_tmp}")

    def do(self, script, user=None):
        try:
            self._before()
            SpawnedSU.do_script(script, bg=False, cmd=self.chroot_cmd(user))
        finally:
            self._after()


class ChrootContext(Chroot):
    def __enter__(self):
        self._before()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._after()

    def do(self, script, user=None) -> Spawned:
        """Run script and wait until it ends"""
        return SpawnedSU.do_script(script, async_=False, bg=False, cmd=self.chroot_cmd(user))

    def doi(self, script, user=None) -> Spawned:
        """Run script and continue execution.
        Returned value can be used as context manager.
        """
        return SpawnedSU.do_script(script, async_=True, bg=False, cmd=self.chroot_cmd(user))


def _cleaner(force=False):
    mp_tpl = MODULE_PFX if force else _TMP
    if mounts := Spawned.do(f'mount | grep "{mp_tpl}" | cut -d" " -f3', list_=True):
        SpawnedSU.do(f'umount {" ".join(mounts)}')


onExit(_cleaner)
