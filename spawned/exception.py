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

"""Child process status"""

from dataclasses import dataclass

__all__ = ['SpawnedChildError', 'ExitReason']


@dataclass(frozen=True)
class ExitReason:
    NORMAL: int = 0
    TERMINATED: int = 1


class SpawnedChildError(Exception):
    """Raised when the child process ends abnormally"""

    def __init__(self, code, reason):
        super().__init__(code, reason)
        self.code = code
        self.reason = reason

    def __str__(self):
        return f"{type(self).__name__}: <CODE: {self.code}>, REASON: {self.reason}"
