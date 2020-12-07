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

"""Runs shell commands in a child subprocess and communicates with them"""

import pexpect
import sys, re
import tempfile

from atexit import register as onExit
from functools import singledispatchmethod
from os import getenv as ENV, getpid as PID, environ as _setenv
from pathlib import Path
from time import time_ns

from .exception import *
from . import logger as log

__all__ = ['Spawned', 'SpawnedSU', 'ask_user', 'onExit', 'ENV', 'SETENV', 'create_py_script']

# internal constants
UPASS = "UPASS"
PIPE = "pipe"
SCRIPT_PFX = "script_"
MODULE_PFX = "spawned_"
TAG = "[Spawned]"
TPL_REQ_UPASS = fr"password for {ENV('USER')}:"

_TMP = Path(tempfile.gettempdir(), f"{__name__}_{PID()}")  # Spawned creates all its stuff there


@log.tagged(TAG, log.ok_blue_s)
def _p(*text): return text


@log.tagged('\n' + TAG, log.ok_blue_s)
def _pn(*text): return text


def _need_upass():
    _, status = pexpect.run("sudo -v", encoding='utf-8', events=[(TPL_REQ_UPASS, lambda d: True)], withexitstatus=True)
    return status  # non-zero status => pattern is found, so the child process is aborted => upass is required


def _cleaner(path, force=False):
    cmd = f"rm -rf {path}; P=$(pgrep {SCRIPT_PFX}) && kill -9 $P"
    S = SpawnedSU if force or Spawned.do(f"pgrep -u root {SCRIPT_PFX}", with_status=True)[0] == 0 else Spawned
    S.do(cmd)


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
                Spawned.waitfor(<mandatory_output>)

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

    def send(self, data):
        if self._child.isalive():
            self._child.sendline(data)

    @singledispatchmethod
    def interact(self, waitfor_pattern, tosend_data, exact=True):
        """
        Waits for any value from ``waitfor_pattern`` and responds with ``tosend_data``.

        :param waitfor_pattern: could be a string or a list of strings
        :param tosend_data: a string to send to the child
        :param exact: should the ``waitfor_pattern`` be treated as a regex or exact string
        :return: index of the matched pattern; 0 if ``waitfor_pattern`` is a string
        """
        idx = self.waitfor(waitfor_pattern, exact=exact)
        if idx is not None:
            if tosend_data == Spawned.TASK_END:
                self._child.terminate(force=True)
            elif tosend_data is not None:
                self.send(tosend_data)
        return idx

    @interact.register(tuple)
    def _(self, *waitfor_tosend_tuples, exact=True):
        """
        Overloaded version of method ``interact()``. ``waitfor_tosend_tuples`` is a list of tuples.
        The method can be invoked as following:

            Spawned.interact((waitfor, tosend), (waitfor, tosend), ..., exact=True)
        """
        waitfor_list = [tupl[0] for tupl in waitfor_tosend_tuples]
        idx = self.waitfor(waitfor_list, exact=exact)
        if idx is not None:
            to_send = waitfor_tosend_tuples[idx][1]
            if to_send == Spawned.TASK_END:
                self._child.terminate(force=True)
            elif to_send is not None:
                self.send(to_send)
        return idx

    def interact_user(self):
        """This gives control of the child process to the human at the keyboard.
        When the user types the 'escape character' (chr(29), i.e. ``Ctrl - ]``) this method returns None.
        The 'escape character' will not be transmitted.
        """
        # prevent:
        # - data duplication in the user's terminal window
        # - app crash: since interact() method needs `bytes` buffer while spawn() method uses `unicode` by default
        if self._child.logfile is sys.stdout:
            self._child.logfile = None

        self._child.interact()
        # restore previous buffer after interactive input ends
        self._child.logfile = self._log_file

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
    def do(command, with_status=False, **kwargs):
        # to avoid bash failure, run as a script if there are special characters in the command
        chars = r"""~!@#$%^&*()+={}\[\]|\\:;"',><?\n"""
        is_special = re.search(f"[{chars}]", command)

        if is_special:
            timeout = kwargs.pop("timeout", Spawned.TO_DEFAULT)
            t = Spawned.do_script(command, async_=True, timeout=timeout, bg=False, **kwargs)
        else:
            t = Spawned(command, **kwargs)

        if with_status:
            t.waitfor(Spawned.TASK_END)
            return t.exit_status
        else:
            return t.data

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
        script_file = Spawned.tmp_file_path(new)
        with script_file.open('w') as f:
            if new:
                f.write(f"#!/bin/bash\n\n{content}")
                script_file.chmod(0o777)
            else:
                f.write(content)
        return script_file

    @staticmethod
    def tmp_file_path(new=True):
        _TMP.mkdir(exist_ok=True)
        return _TMP.joinpath(f'{SCRIPT_PFX}{time_ns()}' if new else PIPE)

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
        return code, reason


class SpawnedSU(Spawned):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, sudo=True, **kwargs)

    @staticmethod
    def do(command, with_status=False, **kwargs):
        return Spawned.do(command, with_status, sudo=True, **kwargs)

    @staticmethod
    def do_script(script: str, async_=False, timeout=Spawned.TO_INFINITE, bg=True, **kwargs):
        return Spawned.do_script(script, async_, timeout, bg, sudo=True, **kwargs)


# register a deleter for the temp storage
onExit(lambda: _cleaner(_TMP))
