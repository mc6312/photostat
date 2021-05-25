#!/usr/bin/env python3
# -*- coding: utf-8 -*-


""" pstat_common.py

    This file is part of PhotoStat.

    PhotoStat is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    PhotoStat is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PhotoStat.  If not, see <http://www.gnu.org/licenses/>."""


from traceback import print_exception


APP_TITLE = 'Сбор статистки параметров фотографий'
APP_VERSION = '1.3'
APP_COPYRIGHT = 'Copyright 2017-2021 MC-6312'
APP_TITLE_VERSION = '%s v%s' % (APP_TITLE, APP_VERSION)


def exception_to_str(ex):
    exs = str(ex)
    if not exs:
        exs = ex.__class__.__name__

    return exs


def dump_exception(enfo=None):
    if enfo is None:
        enfo = sys.exc_info()

    print_exception(*enfo, file=sys.stderr)

