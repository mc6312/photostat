#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  photostat.py

""" Copyright 2017 MC-6312 <mc6312@gmail.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>."""


import sys

from gi import require_version as gi_require_version

gi_require_version('Gtk', '3.0') # извращенцы
from gi.repository import Gtk, Gdk, GObject, Pango, GLib


import os.path

from time import sleep


from psgtktools import *
from psconfig import Configuration
from psstat import *
from pscommon import *
from psabout import *


class PhotoStatUI():
    PAGES_COUNT = 3
    PAGE_PICDIR, PAGE_PROGRESS, PAGE_STAT = range(PAGES_COUNT)
    PAGE_LAST = PAGE_STAT

    PROGRESS_DELAY = 1000 # дергаем прогрессбаром только через PROGRESS_DELAY файлов

    def destroy(self, widget, data=None):
        Gtk.main_quit()

    def __task_events(self):
        # даем прочихаться междумордию
        while Gtk.events_pending():
            Gtk.main_iteration()#False)

    def check_picdirpage_content(self):
        """Проверка правильности заполнения полей
        страницы выбора каталога и типов файлов."""

        self.nextbtn.set_sensitive(self.config.check_fields())

    def pictyperawcb_toggled(self, cbtn, data=None):
        self.config.cfgScanRAWfiles = cbtn.get_active()
        self.check_picdirpage_content()

    def pictypeimgcb_toggled(self, cbtn, data=None):
        self.config.cfgScanImageFiles = cbtn.get_active()
        self.check_picdirpage_content()

    def picdirentry_changed(self, entry, data=None):
        self.config.cfgPhotoRootDir = self.picdirentry.get_text().strip()

        self.check_picdirpage_content()

    def choose_pic_dir(self):
        """Выбор каталога с фотографиями через стандартный диалог"""

        dlg = Gtk.FileChooserDialog('Выбор каталога', self.window,
            Gtk.FileChooserAction.SELECT_FOLDER)

        dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK)

        dlg.set_current_folder(self.config.cfgPhotoRootDir)

        r = dlg.run()

        if r == Gtk.ResponseType.OK:
            self.picdirentry.set_text(dlg.get_current_folder())

        dlg.destroy()

    def scan_progress(self, stats, fpath):
        self.progressDelay -= 1
        if self.progressDelay <= 0:
            self.progressDelay = self.PROGRESS_DELAY

            self.progressbar.pulse()

            #print(stats.statTotalFiles, stats.statTotalPhotos)
            #self.progresstext.set_text('Просмотрено файлов: %d\nИз них учтено: %d' % (stats.statTotalFiles, stats.statTotalPhotos))

        self.__task_events()

        return not self.stopScanning

    def scan_photos(self):
        self.ctlhbox.set_sensitive(False)
        try:
            self.stopScanning = False
            self.progressDelay = self.PROGRESS_DELAY
            self.progressbar.set_sensitive(True)
            # иначе не будет обновляться - при активной странице прогресса всё окно not sensitive!

            self.stats.clear()

            ftypes = set()

            if self.config.cfgScanRAWfiles:
                ftypes.update(RAW_FILE_EXTS)

            if self.config.cfgScanImageFiles:
                ftypes.update(IMAGE_FILE_EXTS)

            e = self.stats.scan_directory(self.config.cfgPhotoRootDir, ftypes, self.scan_progress)
            if e:
                message_dialog(self.window, APP_TITLE, e, Gtk.MessageType.ERROR)

        finally:
            self.ctlhbox.set_sensitive(True)
            self.update_stats_view()
            self.select_next_page() # ибо нефиг после обхода каталогов на этой странице оставаться

    def stop_scanning(self, w, data=None):
        self.stopScanning = True

    def select_next_page(self):
        page = self.pages.get_current_page() + 1

        if page == self.PAGES_COUNT:
            page = 0

        self.nextbtn.set_label('Продолжить' if page < self.PAGE_LAST else 'Начать сначала')

        self.pages.set_current_page(page)

        if page == self.PAGE_PROGRESS:
            self.scan_photos()

    def update_stats_view(self):
        # чистим отображало от старых настроек и значений
        self.statdisplay.set_model(None)

        if self.stattable is not None:
            self.stattable = None

        while self.statdisplay.get_n_columns() > 0:
            self.statdisplay.remove_column(self.statdisplay.get_column(0))

        #
        statdata, ncols = self.stats.get_stat_table()

        # создаем и засираем новую таблицу
        # 1й столбец - заголовок
        # следующие - пары из строки (для отображения)
        # и целого (для прогрессбара)
        coltypes = [GObject.TYPE_STRING] + [GObject.TYPE_STRING, GObject.TYPE_INT] * (ncols - 1)
        self.stattable = Gtk.ListStore(*coltypes)

        self.statdisplay.append_column(Gtk.TreeViewColumn(statdata[0][0], Gtk.CellRendererText(), text=0))

        crpb = Gtk.CellRendererProgress()
        for ixcol in range(ncols - 1):
            dcol = 1 + (ixcol * 2)
            col = Gtk.TreeViewColumn(statdata[0][ixcol + 1], crpb, text=dcol, value=dcol + 1)
            col.set_expand(True)
            self.statdisplay.append_column(col)

        # заполняем данными
        for rowix in range(1, len(statdata)):
            row = statdata[rowix]

            strow = [row[0]]
            for col in row[1:]:
                # пара значений - строка для отображения
                strow.append(str(col) if col > 0 else '')

                # и значение для прогрессбара
                p = 0 if self.stats.statTotalPhotos == 0 else col * 100 / self.stats.statTotalPhotos

                strow.append(p)

            self.stattable.append(strow)

        #
        self.statdisplay.set_model(self.stattable)

    def __init__(self, config):
        """Создание окна с виджетами.
        config - экземпляр Configuration."""

        self.config = config
        self.stopScanning = False
        self.progressDelay = self.PROGRESS_DELAY
        self.stats = PhotoStatistics()

        self.window = Gtk.Window()
        self.window.connect('destroy', self.destroy)

        self.window.set_title(APP_TITLE)
        load_icon(self.window)

        self.window.set_border_width(WIDGET_SPACING)
        self.window.set_size_request(800, 600)

        rootvbox = Gtk.VBox(spacing=WIDGET_SPACING)
        self.window.add(rootvbox)

        self.pages = Gtk.Notebook()
        # делаем страницы визарда вручную - потому что Gtk.Assistant попросту уёбищен
        rootvbox.pack_start(self.pages, True, True, 0)

        self.pages.set_show_tabs(False)
        self.pages.set_show_border(False)

        #
        # Страница 1: выбор каталога и типов файлов
        #

        self.picdirpage = Gtk.VBox(spacing=WIDGET_SPACING)

        # выбор каталога
        picdirfr, picdirbox = frame_with_box('Каталог с фотографиями:', Gtk.HBox)

        self.picdirpage.pack_start(picdirfr, False, False, 0)

        #print(self.config)

        self.picdirentry = Gtk.Entry()
        self.picdirentry.set_text(self.config.cfgPhotoRootDir)
        self.picdirentry.connect('changed', self.picdirentry_changed)
        picdirbox.pack_start(self.picdirentry, True, True, 0)

        picdirbtn = Gtk.Button('Выбрать')
        picdirbtn.connect('clicked', lambda b: self.choose_pic_dir())
        picdirbox.pack_end(picdirbtn, False, False, 0)

        # выбор типа файлов
        pictypefr, pictypebox = frame_with_box('Типы файлов')
        self.picdirpage.pack_start(pictypefr, False, False, 0)

        for btitle, bstate, btoggled in (('RAW', self.config.cfgScanRAWfiles, self.pictyperawcb_toggled),
            ('JPEG, PNG, TIFF', self.config.cfgScanImageFiles, self.pictypeimgcb_toggled)):

            checkbtn = Gtk.CheckButton.new_with_label(btitle)
            checkbtn.set_active(bstate)
            checkbtn.connect('toggled', btoggled)

            pictypebox.pack_start(checkbtn, False, False, 0)

        self.pages.append_page(self.picdirpage)

        #
        # Страница 2: сбор статистики
        #

        self.progresspage = Gtk.VBox(spacing=WIDGET_SPACING)

        self.progresstext = Gtk.Label('Сбор статистики...')
        self.progresstext.set_halign(0.0)


        self.progresspage.pack_start(self.progresstext, True, True, 0)

        pbhbox = Gtk.HBox(spacing=WIDGET_SPACING)
        self.progresspage.pack_end(pbhbox, False, False, 0)

        self.progressbar = Gtk.ProgressBar()
        #self.progressbar.set_show_text(True)
        pbhbox.pack_start(self.progressbar, True, True, 0)

        self.progressstopbtn = Gtk.Button('Прервать')
        self.progressstopbtn.connect('clicked', self.stop_scanning)
        pbhbox.pack_end(self.progressstopbtn, False, False, 0)

        self.pages.append_page(self.progresspage)

        #
        # Страница 3: отображение статистики
        #

        self.statdisppage = Gtk.VBox(spacing=WIDGET_SPACING)

        sdfr, sdbox = frame_with_box('Статистика')
        self.statdisppage.pack_start(sdfr, True, True, 0)

        # сюда вкрачить Gtk.TreeView
        self.stattable = None # ибо кол-во столбцов зависит от собранной статистики
        self.statdisplay = Gtk.TreeView()

        sdscwindow = Gtk.ScrolledWindow()
        sdscwindow.set_shadow_type(Gtk.ShadowType.IN)
        sdscwindow.add(self.statdisplay)

        sdbox.pack_start(sdscwindow, True, True, 0)

        # сохранение статистики

        sdsavebox = Gtk.HBox(spacing=WIDGET_SPACING)
        self.statdisppage.pack_end(sdsavebox, False, False, 0)

        sdsavefilebtn = Gtk.Button('Сохранить в файл')
        sdsavefilebtn.connect('clicked', lambda b: self.save_stat_to_file())
        sdsavebox.pack_start(sdsavefilebtn, False, False, 0)

        sdcopytocbbtn = Gtk.Button('Скопировать в буфер обмена')
        sdcopytocbbtn.connect('clicked', lambda b: self.copy_stat_to_clipboard())
        sdsavebox.pack_start(sdcopytocbbtn, False, False, 0)

        self.pages.append_page(self.statdisppage)

        #
        # управление
        #

        rootvbox.pack_start(Gtk.HSeparator(), False, False, 0)

        self.ctlhbox = Gtk.HBox(spacing=WIDGET_SPACING)
        rootvbox.pack_end(self.ctlhbox, False, False, 0)

        self.nextbtn = Gtk.Button('Продолжить')
        self.nextbtn.set_can_default(True   )
        self.nextbtn.connect('clicked', lambda b: self.select_next_page())
        self.ctlhbox.pack_start(self.nextbtn, False, False, 0)

        exitbtn = Gtk.Button('Выход')
        exitbtn.connect('clicked', self.destroy)
        self.ctlhbox.pack_end(exitbtn, False, False, 0)

        aboutbtn = Gtk.Button('О программе')
        aboutbtn.connect('clicked', lambda b: AboutDialog(self.window).run())
        self.ctlhbox.pack_end(aboutbtn, False, False, 0)

        #
        #
        #

        self.pages.set_current_page(self.PAGE_PICDIR)
        self.window.show_all()

        self.check_picdirpage_content() # ибо какие-то параметры уже указаны

    def save_stat_to_file(self):
        def get_save_file_name():
            dlg = Gtk.FileChooserDialog('Сохранение статистики в файл', self.window,
                Gtk.FileChooserAction.SAVE)

            dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK)

            fdir, fname = os.path.split(self.config.cfgStatSaveFile)
            dlg.set_current_folder(fdir)
            dlg.set_current_name(fname)

            for fltname, fltpat in (('Текстовые файлы', '*.txt'), ('Все файлы', '*.*')):
                fltr = Gtk.FileFilter()
                fltr.set_name(fltname)
                fltr.add_pattern(fltpat)
                dlg.add_filter(fltr)

            r = dlg.run()
            if r == Gtk.ResponseType.OK:
                self.config.cfgStatSaveFile = dlg.get_filename()

            dlg.destroy()

            return r == Gtk.ResponseType.OK

        if get_save_file_name():
            try:
                #raise ValueError('Boo!')
                with open(self.config.cfgStatSaveFile, 'w+') as f:
                    f.write(self.stats.get_stat_table_str())
            except Exception as ex:
                message_dialog(self.window, 'Сохранение статистики в файл',
                               'Не удалось сохранить файл.\n%s' % exception_to_str(ex))

    def copy_stat_to_clipboard(self):
        try:
            cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            cb.clear()
            cb.set_text(self.stats.get_stat_table_str(), -1)
            cb.store()
        except Exception as ex:
            message_dialog(self.window, 'Копирование статистики в буфер обмена',
                           'Сбой при операции с буфером обмена - %s' % exception_to_str(ex))

    def main(self):
        Gtk.main()


def save_load_settings(config, save):
    e = config.save() if save else config.load()

    if e:
        message_dialog(None, '%s - %s настроек' % (APP_TITLE, 'сохранение' if save else'загрузка'),
                       e, Gtk.MessageType.ERROR)
        return False

    return True


def main():
    config = Configuration(get_config_file_name())

    if not save_load_settings(config, False):
        return 1

    PhotoStatUI(config).main()

    if not save_load_settings(config, True):
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
