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

"""Runs shell commands in a child subprocess and communicates with them"""

import argparse
import pexpect
import sys, re
import tempfile

from atexit import register as onExit
from importlib.metadata import version as app_version
from os import getenv as ENV, getpid as PID, environ as _setenv
from pathlib import Path
from time import time_ns

from .exception import *
from . import logger as log

__author__ = "Roman Gladyshev"
__email__ = "remicollab@gmail.com"
__copyright__ = "Copyright (c) 2020, REMICO"
__license__ = "LGPLv3+"

__all__ = ['Spawned', 'SpawnedSU', 'ask_user', 'onExit', 'ENV', 'SETENV', 'create_py_script']

# internal constants
UPASS = "UPASS"
PIPE = "pipe"
SCRIPT_PFX = "script_"
MODULE_PFX = "spawned_"
TAG = "[Spawned]"
TPL_REQ_UPASS = fr"password for {ENV('USER')}:"

_TMP = Path(tempfile.gettempdir(), f'{__name__}_{PID()}')  # Spawned creates all its stuff there


@log.tagged(TAG, log.ok_blue_s)
def _p(*text): return text


@log.tagged('\n' + TAG, log.ok_blue_s)
def _pn(*text): return text


def _need_upass():
    _, status = pexpect.run("sudo -v", encoding='utf-8', events=[(TPL_REQ_UPASS, lambda d: True)], withexitstatus=True)
    return status  # non-zero status => pattern is found, so the child process is aborted => upass is required


def _cleaner(path):
    return f"rm -rf {path}; P=$(pgrep {SCRIPT_PFX}) && kill -9 $P"


def SETENV(key, value):
    assert isinstance(value, str), "SETENV: environment variable must be of string type"
    _setenv[key] = value


def TPL_CMD_DO_SCRIPT(nohup: bool):
    # f'bash -c "nohup {script_file} > /dev/null 2>&1 &"'  # nohup alternative
    return 'bash -c "{} &"' if nohup else 'bash "{}"'


def ask_user(prompt):
    tag = log.header_s('\n[' + log.blink_s("<<< ??? >>>") + ']')
    return input(f"{tag} {prompt} ")


def create_py_script(script: str):
    _TMP.mkdir(exist_ok=True)
    script_file = _TMP.joinpath(f'{SCRIPT_PFX}{time_ns()}.py')
    with script_file.open('w') as f:
        f.write(f"#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\n{script.strip()}")
    return script_file


class Spawned:
    TO_DEFAULT = -1
    TO_INFINITE = None
    TASK_END = pexpect.EOF
    ANSWER_DEFAULT = ""

    _log_commands = False
    _log_file = None
    _need_upass = _need_upass()

    def __init__(self, command, args=[], **kwargs):
        # note: pop extra arguments from kwargs before passing it to pexpect.spawn()
        if kwargs.pop('sudo', False):
            user_opt = f'-u {user}' if (user := kwargs.pop('user', None)) else ''
            command = f"sudo {user_opt} {command}"

        # debugging output
        if Spawned._log_commands:
            self._print_command(command)

        su = command.startswith("sudo") and Spawned._need_upass
        assert not su or ENV(UPASS), "User password isn't specified while 'sudo' is used. Exit..."

        timeout = kwargs.get('timeout', None)
        if timeout == Spawned.TO_DEFAULT:  # remove local alias, so spawn will use its own default timeout value
            del kwargs['timeout']
        else:
            assert timeout is None or timeout > 0, "'timeout' value (in sec) must be > 0"

        self._child = pexpect.spawn(command, args, encoding='utf-8', logfile=self.log_file, echo=False, **kwargs)

        if su:
            self.interact(TPL_REQ_UPASS, ENV(UPASS))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.waitfor(Spawned.TASK_END)

    def waitfor(self, pattern, exact=True, timeout=TO_DEFAULT):
        """The program will be terminated if nothing from ``pattern`` is caught in the child's output.
        Thus the method can usually be used in 2 use cases:

            - like a runtime assertion check:
                Spawned.waitfor(<a_mandatory_output>)

            - wait for the child process end:
                Spawned.waitfor(Spawned.TASK_END)
        """
        try:
            if self._child.isalive():
                expect = self._child.expect_exact if exact else self._child.expect
                return expect(pattern, timeout)

        except pexpect.EOF:
            _pn(log.fail_s("Child unexpected EOF. Was expected one of: [%s]." % pattern))
            if ask_user("Abort application? [y/n]:").lower() == 'y':
                sys.exit("\nABORTED BY USER")

        except pexpect.TIMEOUT:
            _pn(log.fail_s("Child TIMEOUT"))
            self._child.close()
            if ask_user("Abort application? [y/n]:").lower() == 'y':
                sys.exit("\nABORTED BY USER")

    def send(self, pattern):
        if self._child.isalive():
            self._child.sendline(pattern)

    def interact(self, waitfor_pattern, send_pattern, exact=True):
        idx = self.waitfor(waitfor_pattern, exact=exact)
        if idx is not None:
            assert_message = f"No valid response defined for expected index {idx}"
            if isinstance(send_pattern, list):
                assert len(send_pattern) >= idx + 1, assert_message
                to_send = send_pattern[idx]
            else:
                assert idx == 0, assert_message
                to_send = send_pattern

            if to_send == Spawned.TASK_END:
                self._child.terminate(force=True)
            elif to_send is not None:
                self.send(to_send)

    @staticmethod
    def _print_command(command):
        # see the command
        _p("@ COMMAND:", command)
        # explore the command's content
        if mo := re.search(fr'"(.*{PIPE})"', command):
            pipe_path = Path(mo.group(1))
            if pipe_path.exists():
                _p("@ PIPE:", pipe_path.read_text())

    @staticmethod
    def do(command, args=[], **kwargs):
        # to avoid bash failure, run as a script if there are special characters in the command
        chars = r"""~!@#$%^&*()+={}\[\]|\\:;"',><?\n"""
        is_special = re.search(f"[{chars}]", command) or (any(re.search(f"[{chars}]", arg) for arg in args))
        if is_special:
            # hack: join all the arguments to a single string command
            command = f"{command} {' '.join(args)}"
            timeout = kwargs.pop("timeout", Spawned.TO_DEFAULT)
            t = Spawned.do_script(command, async_=True, timeout=timeout, bg=False, **kwargs)
        else:
            t = Spawned(command, args=args, **kwargs)
        data_string = t.data
        t.waitfor(Spawned.TASK_END)
        return data_string

    @staticmethod
    def do_script(script: str, async_=False, timeout=TO_INFINITE, bg=True, **kwargs):
        """Runs a multiline bunch of commands in form of a bash script

        :param script: a multiline string, think of it as of a in regular bash script file
        :param async_: if True, waits until the script ends; returns immediately otherwise
        :param timeout: if None, no timeout is set; if ``TO_DEFAULT``, uses default pexpect's timeout;
            actual timeout (in sec) otherwise
        :param bg: if True, creates a temporary executable script and run it in background, unbounded from
            the parent process. Actual ``async_`` value isn't taken into account in this case, and treated as True,
            because after the script is created and run, the parent bash process will just exit immediately.
            Note: always use ``bg=False`` if you need to process the script's output data.
        :return: a :class:`Spawned` instance. Returned value is quite useless if ``bg`` is True.
        """

        pipe_file = Spawned._file_it(script.strip(), new=bg)
        cmd_tpl = kwargs.pop('cmd', TPL_CMD_DO_SCRIPT(bg))
        cmd = cmd_tpl.format(pipe_file)

        t = Spawned(cmd, timeout=timeout, ignore_sighup=bg, **kwargs)
        if not async_:
            t.waitfor(Spawned.TASK_END)
        return t

    @staticmethod
    def _file_it(content, new=True):
        _TMP.mkdir(exist_ok=True)
        script_file = _TMP.joinpath(f'{SCRIPT_PFX}{time_ns()}' if new else PIPE)
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
        return self._child.read().strip() if self._child.isalive() else ''

    @property
    def datalines(self):
        return self._child.readlines() if self._child.isalive() else []

    @property
    def exit_status(self):
        """Call child.close() before calling this.
        Alternatively, call this after EOF is reached, i.e. after Spawned.waitfor(TASK_END).
        Otherwise the exit reason is always 0 and actual exit status is undefined (None).
        """
        self._child.isalive()  # update exit status from child's internals
        reason = ExitReason.NORMAL if self._child.signalstatus is None else ExitReason.TERMINATED
        code = self._child.exitstatus if reason == ExitReason.NORMAL else self._child.signalstatus
        return reason, code


class SpawnedSU(Spawned):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, sudo=True, **kwargs)

    @staticmethod
    def do(command, args=[], **kwargs):
        return Spawned.do(command, args=args, sudo=True, **kwargs)

    @staticmethod
    def do_script(script: str, async_=False, timeout=Spawned.TO_INFINITE, bg=True, **kwargs):
        return Spawned.do_script(script, async_, timeout, bg, sudo=True, **kwargs)


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
