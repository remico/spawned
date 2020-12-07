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

import argparse
import sys
import tempfile
from pathlib import Path
from importlib.metadata import version as app_version

from .chroot import _cleaner as _cleaner_chroot
from .spawned import Spawned, SETENV, UPASS, MODULE_PFX, _cleaner as _cleaner_spawned


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-c", "--clean", action="store_true",
                           help="Removes all Spawned-related stuff from the temp-storage recursively"
                                " and kills all Spawned's background processes."
                                " Needs superuser privileges (use -p option).")
    argparser.add_argument("-p", type=str, metavar="PASSWORD", help="User password")
    argparser.add_argument("-d", action="store_true", help="Enable debug output")
    argparser.add_argument("-v", action="store_true", help="Verbose mode")
    argparser.add_argument("--version", action="store_true", help="Show version and exit")
    op = argparser.parse_args()

    # set password before any Spawned runs
    if op.p:
        SETENV(UPASS, op.p)

    if op.d:
        Spawned.enable_debug_commands()

    if op.v:
        Spawned.enable_logging()

    if op.version:
        print(app_version(__package__))
        sys.exit()

    if op.clean:
        to_remove = Path(tempfile.gettempdir(), f'{{*{MODULE_PFX}*,*__main__*}}')
        _cleaner_spawned(to_remove, True)
        _cleaner_chroot(True)


if __name__ == '__main__':
    main()
