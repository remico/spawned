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

"""Child process status"""

from dataclasses import dataclass

__author__ = "Roman Gladyshev"
__email__ = "remicollab@gmail.com"
__copyright__ = "Copyright (c) 2020, REMICO"
__license__ = "LGPLv3+"

__all__ = ['SpawnedChildError', 'ExitReason']


@dataclass(frozen=True)
class ExitReason:
    NORMAL: int = 0
    TERMINATED: int = 1


class SpawnedChildError(Exception):
    """Raised when the child process ends abnormally"""

    def __init__(self, reason, code):
        super().__init__(reason, code)
        self.reason = reason
        self.code = code

    def __str__(self):
        return f"{type(self).__name__}: <REASON: {self.reason}, CODE: {self.code}>"
