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


from gtktools import *
from gi.repository import Gtk, GObject, Pango

from pstat_common import *
from pstat_config import *


class AboutDialog():
    def __init__(self, parentwnd):
        resldr = get_resource_loader()

        self.dlgabout = Gtk.AboutDialog(parent=parentwnd)

        self.dlgabout.set_copyright(APP_COPYRIGHT)
        self.dlgabout.set_version('v%s' % APP_VERSION)
        self.dlgabout.set_program_name(APP_TITLE)

        # загрузка ресурсов
        iconsize = WIDGET_BASE_WIDTH * 24

        icon = resldr.load_pixbuf('photostat.svg', iconsize, iconsize)
        if icon:
            self.dlgabout.set_logo(icon)

        if resourcePaths.license:
            try:
                with open(resourcePaths.license, 'r') as f:
                    slicense = f.read().strip()

            except OSError:
                slicense = None
        else:
            slicense = None

        self.dlgabout.set_license_type(Gtk.License.GPL_3_0_ONLY)
        self.dlgabout.set_license(slicense if slicense else 'Файл с текстом GPL не найден.\nИщите на http://www.fsf.org/')

        self.dlgabout.add_credit_section('Сляпано во славу',
            ['Азатота', 'Йог-Сотота', 'Ктулху', 'Шаб-Ниггурат', 'и прочей кодлы Великих Древних'])
        self.dlgabout.add_credit_section('Особая благодарность', ['Левой ноге автора'])

    def run(self):
        self.dlgabout.show_all()
        self.dlgabout.run()
        self.dlgabout.hide()


if __name__ == '__main__':
    print('[debugging %s]' % __file__)

    AboutDialog(None).run()
