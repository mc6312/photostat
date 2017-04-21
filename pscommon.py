#!/usr/bin/env python3
# -*- coding: utf-8 -*-


""" This file is part of PhotoStat.

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


APP_TITLE = 'Сбор статистки параметров фотографий'
APP_VERSION = u'1.1'
APP_COPYRIGHT = u'Copyright 2017 MC-6312'


def exception_to_str(ex):
    exs = str(ex)
    if not exs:
        exs = ex.__class__.__name__

    return exs
