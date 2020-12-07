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

"""Simple functions for logging in color"""


def _e(key):
    return '\033[%sm' % key


_RESETALL = _e(0)
_ENDBOLD = _e(21)
_ENDUNDERLINE = _e(24)
_ENDBLINK = _e(25)
_ENDCOLOR = _e(39)

_BOLD = _e(1)
_UNDERLINE = _e(4)
_BLINK = _e(5)

_MAGENTA = _e(95)
_BLUE = _e(94)
_GREEN = _e(92)
_YELLOW = _e(93)
_RED = _e(91)


def _wrap(tag, value):
    if tag == _BOLD:
        etag = _ENDBOLD
    elif tag == _UNDERLINE:
        etag = _ENDUNDERLINE
    elif tag == _BLINK:
        etag = _ENDBLINK
    elif tag:
        etag = _ENDCOLOR
    else:
        tag = ''
        etag = ''
    return tag + value + etag


def _out(tag, *text, **kwargs):
    content = ' '.join(text).replace(_RESETALL, '')  # avoid multiple format resetting
    resetall = _RESETALL if not kwargs.pop('noreset', False) else ''
    s = _wrap(tag, content) + resetall
    return print(s, **kwargs) if not kwargs.pop("str", False) else s


def _str(f):
    def mkstr(*args, **kwargs):
        return f(*args, **kwargs, str=True)
    fname = f.__name__ + '_s'
    globals()[fname] = mkstr
    return f


def tagged(tag, formatter):
    def f(func):
        def w(*args, **kwargs):
            print(formatter(tag), *func(*args), **kwargs)
        return w
    return f


@_str
def blink(*text, **kwargs):
    return _out(_BLINK, *text, **kwargs)


@_str
def bold(*text, **kwargs):
    return _out(_BOLD, *text, **kwargs)


@_str
def underline(*text, **kwargs):
    return _out(_UNDERLINE, *text, **kwargs)


@_str
def header(*text, **kwargs):
    return _out(_MAGENTA, *text, **kwargs)


@_str
def ok_blue(*text, **kwargs):
    return _out(_BLUE, *text, **kwargs)


@_str
def ok_green(*text, **kwargs):
    return _out(_GREEN, *text, **kwargs)


@_str
def warning(*text, **kwargs):
    return _out(_YELLOW, *text, **kwargs)


@_str
def fail(*text, **kwargs):
    return _out(_RED, *text, **kwargs)


def print_dict(self):
    T = type(self)
    # <type> :: all the instance attributes, with their values
    print(f"{T} :: {self.__dict__}")
    # all @property fields of the instance, with their values
    property_names = [p for p in dir(T) if isinstance(getattr(T, p), property)]
    for n in property_names:
        default_value = fail('>> ATTRIBUTE ERROR <<', str=True)
        print(f"{n} : {getattr(self, n, default_value)}")


if __name__ == '__main__':
    pass
