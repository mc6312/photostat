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


from gi.repository import Gtk, GLib
from gi.repository.GdkPixbuf import Pixbuf

import sys

from psconfig import *


WIDGET_SPACING = 4


def frame_with_box(title, boxclass=Gtk.VBox):
    frame = Gtk.Frame.new(title)

    box = boxclass(spacing=WIDGET_SPACING)
    box.set_border_width(WIDGET_SPACING)
    frame.add(box)

    return (frame, box)


def set_widgets_sensitive(widgetlist, sensitive):
    for widget in widgetlist:
        widget.set_sensitive(sensitive)


def message_dialog(parent, title, msg, icon=Gtk.MessageType.INFO):
    dlg = Gtk.MessageDialog(parent, Gtk.DialogFlags.MODAL,
        icon,
        Gtk.ButtonsType.OK,
        msg)
    dlg.set_title(title)

    dlg.run()
    dlg.destroy()


def load_icon(window=None):
    """Загрузка иконы (логотипа) приложения.

    window  - окно, для которого устанавливать икону
              если None - ф-я возвращает экземпляр Pixbuf
              если Gtk.Window - устанавли

    Возвращает экземпляр Pixbuf в случае успеха, иначе None."""

    try:
        if resourcePaths.logotype:
            if window is not None:
                window.set_icon_from_file(resourcePaths.logotype)
            else:
                return Pixbuf.new_from_file(resourcePaths.logotype) #_at_size(..., xsize, ysize)

    except GLib.GError:
        print(u'Не удалось загрузить файл изображения "%s"' % resourcePaths.logotype, file=sys.stderr)

        if window is None:
            return self.window.render_icon_pixbuf(Gtk.STOCK_ABOUT, Gtk.IconSize.DIALOG)


if __name__ == '__main__':
    #raise Exception('I am module!')
    #message_dialog(None, 'Foo', 'Boo!')
    print(load_icon())
