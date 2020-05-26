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

""" Runs shell commands in a child subprocess and communicates with them"""

import argparse
import pexpect
import sys, re
import tempfile
from atexit import register as onExit
from importlib.metadata import version as app_version
from os import getenv as ENV, getpid as PID, environ as _setenv
from pathlib import Path
from time import time_ns
from . import logger as log

__author__ = "Roman Gladyshev"
__email__ = "remicollab@gmail.com"
__copyright__ = "Copyright (c) 2020, REMICO"
__license__ = "LGPLv3+"

__all__ = ['Spawned', 'SpawnedSU', 'ask_user', 'onExit', 'ENV', 'SETENV']

# internal constants
UPASS = "UPASS"
FIFO = "fifo"
SCRIPT_PFX = "script_"
MODULE_PFX = "spawned_"
TAG = "[Spawned]"


_TMP = Path(tempfile.gettempdir(), f'{__name__}_{PID()}')  # Spawned creates all its stuff there


@log.tagged(TAG, log.ok_blue_s)
def _p(*text): return text


@log.tagged('\n' + TAG, log.ok_blue_s)
def _pn(*text): return text


def SETENV(key, value):
    assert isinstance(value, str), "SETENV: environment variable must be of string type"
    _setenv[key] = value


def ask_user(prompt):
    tag = log.warning_s('\n[' + log.blink_s(TAG) + ']')
    return input(f"{tag} {prompt} ")


class Spawned:
    TO_DEFAULT = -1
    TO_INFINITE = None
    TASK_END = pexpect.EOF
    ANSWER_DEFAULT = ""

    _log_commands = False
    _log_file = None

    def __init__(self, command, args=[], **kwargs):
        # note: pop extra arguments from kwargs before passing it to pexpect.spawn()
        command = f"{'sudo ' if kwargs.pop('sudo', False) else ''}{command}"

        # ## DEBUG: LOG COMMANDS ##
        if Spawned._log_commands:
            # see the command
            _p("@ COMMAND:", command)
            # explore the command's content
            if mo := re.search(fr'"(.*{FIFO})"', command):
                with open(mo.group(1)) as f:
                    _p("@ FIFO:", f.read())
        # #########################

        # user password, useful for sudo
        upass = kwargs.pop('upass', ENV(UPASS))

        # set reasonable timeout
        timeout = 30 if (t := kwargs.pop('timeout', 30)) == Spawned.TO_DEFAULT else t
        assert (timeout is None) or (timeout > 0) or (timeout == Spawned.TO_DEFAULT), "Bad 'timeout' value"

        self._child = pexpect.spawn(command, args, encoding='utf-8', timeout=timeout,
                                    logfile=self.log_file, echo=False, **kwargs)

        # let's cheat a bit
        if command.startswith("sudo") and upass:
            self.interact("[sudo] password for", upass)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.waitfor(Spawned.TASK_END)

    def waitfor(self, pattern, exact=True, timeout_s=TO_DEFAULT):
        try:
            if exact:
                self._child.expect_exact(pattern, timeout_s)
            else:
                self._child.expect(pattern, timeout_s)
            return True
        except pexpect.EOF:
            _p("{%s} haven't been caught. EOF reached." % pattern)
            sys.exit("\nTERMINATED")
        except pexpect.TIMEOUT:
            _pn(log.warning_s("TIMEOUT"))

    def send(self, pattern):
        self._child.sendline(pattern)

    def interact(self, waitfor_pattern, send_pattern, exact=True):
        if self.waitfor(waitfor_pattern, exact):
            self.send(send_pattern)

    @staticmethod
    def do(command, args=[], **kwargs):
        # to avoid bash failure, run as a script if there are special characters in the command
        chars = r"""~!@#$%^&*()+={}\[\]|\\:;"',><?"""
        is_special = re.search(f"[{chars}]", command) or (any(re.search(f"[{chars}]", arg) for arg in args))
        if is_special:
            # hack: join all the arguments to a single string command
            command = f"{command} {' '.join(args)}"
            t = Spawned.do_script(command, async_=True, timeout_s=Spawned.TO_DEFAULT, bg=False, **kwargs)
        else:
            t = Spawned(command, args=args, **kwargs)
        data_string = t.data
        t.waitfor(Spawned.TASK_END)
        return data_string

    @staticmethod
    def do_script(script: str, async_=False, timeout_s=TO_INFINITE, bg=True, **kwargs):
        """Runs a multiline bunch of commands in form of a bash script

        :param script: a multiline string, think of it as of a in regular bash script file
        :param async_: if True, waits until the script ends; returns immediately otherwise
        :param timeout_s: if None, no timeout is set; if -1, uses default internal timeout (30 sec);
            actual timeout in sec otherwise
        :param bg: if True, creates a temporary executable script and run it in background, unbounded from
            the parent process. Actual ``async_`` value isn't taken into account in this case, and treated as True,
            because after the script is created and run, the parent bash process will just exit immediately.
            Note: always use ``bg=False`` if you need to process the script's output data.
        :return: a :class:`Spawned` instance. Returned value is quite useless if ``bg`` is True.
        """
        script = script.strip()

        if bg:
            script_file = Spawned._file_it(script)
            cmd = f'/bin/bash -c "{script_file} &"'
            # cmd = f'/bin/bash -c "nohup {script_file} > /dev/null 2>&1 &"'  # alternative
        else:
            fifo = Spawned._file_it(script, new=False)
            cmd = f'/bin/bash "{fifo}"'

        t = Spawned(cmd, timeout=timeout_s, ignore_sighup=bg, **kwargs)
        if not async_:
            t.waitfor(Spawned.TASK_END)
        return t

    @staticmethod
    def make_script_py(script: str):
        _TMP.mkdir(exist_ok=True)
        script_file = _TMP.joinpath(f'{SCRIPT_PFX}{time_ns()}.py')
        with script_file.open('w') as f:
            f.write(f"#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\n{script.strip()}")
        return script_file

    @staticmethod
    def _file_it(content, new=True):
        _TMP.mkdir(exist_ok=True)
        script_file = _TMP.joinpath(FIFO if not new else f'{SCRIPT_PFX}{time_ns()}')
        with script_file.open('w') as f:
            if new:
                f.write(f"#!/bin/bash\n\n{content}")
                script_file.chmod(0o777)
            else:
                f.write(content)
        return script_file

    @staticmethod
    def enable_debug_commands(enable=True):
        Spawned._log_commands = enable

    @staticmethod
    def enable_logging(file=sys.stdout):
        """If ``file`` is a regular file, calling this method will truncate it"""
        Spawned._log_file = file
        if isinstance(file, str):
            open(file, "w").close()  # truncate the log file

    @property
    def log_file(self):
        return open(f, "a") if isinstance(f := Spawned._log_file, str) else f

    @property
    def data(self):
        return self._child.read().strip()

    @property
    def datalines(self):
        return self._child.readlines()


class SpawnedSU(Spawned):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, sudo=True, **kwargs)

    @staticmethod
    def do(command, args=[], **kwargs):
        Spawned.do(command, args=args, sudo=True, **kwargs)

    @staticmethod
    def do_script(script: str, async_=False, timeout_s=Spawned.TO_INFINITE, bg=True, **kwargs):
        Spawned.do_script(script, async_, timeout_s, bg, sudo=True, **kwargs)


def _cleaner(path):
    return f"rm -rf {path}; P=$(pgrep {SCRIPT_PFX}) && kill -9 $P"


def run():
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
        stuff_to_remove = Path(tempfile.gettempdir(), f'{{*{MODULE_PFX}*,*__main__*}}')
        SpawnedSU.do(_cleaner(stuff_to_remove))


if __name__ == '__main__':
    run()


# register a deleter for the temp storage
onExit(lambda: Spawned.do(f"pgrep -u root {SCRIPT_PFX}") and SpawnedSU.do(_cleaner(_TMP)) or Spawned.do(_cleaner(_TMP)))
