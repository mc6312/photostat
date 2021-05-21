#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  photostat.py

""" Copyright 2017-2021 MC-6312

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


from gtktools import *
from gi.repository import Gtk, Gdk, GObject, Pango, GLib

import sys
import os.path

from time import sleep

from pstat_config import Configuration
from pstat_stat import *
from pstat_common import *
from pstat_about import *


class PhotoStatUI():
    PAGES_COUNT = 3
    PAGE_START, PAGE_PROGRESS, PAGE_RESULT = range(PAGES_COUNT)
    PAGE_LAST = PAGE_RESULT

    PROGRESS_DELAY = 1000 # дергаем прогрессбаром только через PROGRESS_DELAY файлов

    def wnd_destroy(self, widget, data=None):
        Gtk.main_quit()

    def scan_progress(self, stats, fpath):
        self.progressDelay -= 1
        if self.progressDelay <= 0:
            self.progressDelay = self.PROGRESS_DELAY

            self.progressBar.pulse()

            #print(stats.statTotalFiles, stats.statTotalPhotos)
            self.txtProgress.set_text('Просмотрено файлов: %d\nИз них учтено: %d' % (stats.statTotalFiles, stats.statTotalPhotos))

        flush_gtk_events()

        return not self.stopScanning

    def scan_photos(self):
        try:
            self.stopScanning = False
            self.progressDelay = self.PROGRESS_DELAY
            #self.progressBar.set_sensitive(True)
            # иначе не будет обновляться - при активной странице прогресса всё окно not sensitive!

            self.stats.clear()

            ftypes = set()

            if self.config.cfgScanRAWfiles:
                ftypes.update(RAW_FILE_EXTS)

            if self.config.cfgScanImageFiles:
                ftypes.update(IMAGE_FILE_EXTS)

            e = self.stats.scan_directory(self.config.cfgPhotoRootDir, ftypes, self.scan_progress)
            if e:
                msg_dialog(self.window, APP_TITLE, e)

        finally:
            self.update_stats_view()
            self.select_next_page(False) # ибо нефиг после обхода каталогов на этой странице оставаться

    def stop_scanning(self):
        self.stopScanning = True
        self.pages.set_current_page(self.PAGE_START)

    def select_next_page(self, byButton):
        if byButton:
            page = self.PAGE_PROGRESS if self.curPage == self.PAGE_START else self.PAGE_START
        else:
            page = self.curPage + 1
            if page == self.PAGES_COUNT:
                page = self.PAGE_START

        self.pages.set_current_page(page)

        if page == self.PAGE_PROGRESS:
            self.scan_photos()

    def update_stats_view(self):
        # чистим отображало от старых настроек и значений
        self.faSummary.refresh_begin()
        # т.к. ниже будем создавать новый экземпляр Gtk.ListStore
        self.faSummary.store = None

        while self.faSummary.view.get_n_columns() > 0:
            self.faSummary.view.remove_column(self.faSummary.view.get_column(0))

        #
        stat = self.stats.get_stat_table()

        if stat.rows:
            # создаем и засираем новую таблицу
            # 1й столбец - заголовок
            # следующие - пары из строки (для отображения)
            # и целого (для прогрессбара)

            lastcol = len(stat.rows[0]) - 1

            coltypes = [GObject.TYPE_STRING] + [GObject.TYPE_STRING, GObject.TYPE_INT] * lastcol

            self.faSummary.store = Gtk.ListStore(*coltypes)

            self.faSummary.view.append_column(Gtk.TreeViewColumn(stat.rows[0][0], Gtk.CellRendererText(), text=0))

            crpb = Gtk.CellRendererProgress()
            crpb.set_property('text-xalign', 0.0)

            for ixcol in range(lastcol):
                dcol = 1 + (ixcol * 2)
                col = Gtk.TreeViewColumn(stat.rows[0][ixcol + 1], crpb, text=dcol, value=dcol + 1)
                col.set_expand(True)
                self.faSummary.view.append_column(col)

            # заполняем данными
            for rowix in range(1, len(stat.rows)):
                row = stat.rows[rowix]

                strow = [row[0]]
                for col in row[1:]:
                    # пара значений - строка для отображения
                    strow.append(str(col) if col > 0 else '')

                    # и значение для прогрессбара
                    p = 0 if self.stats.statTotalPhotos == 0 else col * 100 / self.stats.statTotalPhotos

                    strow.append(p)

                self.faSummary.store.append(strow)

            #
            self.faSummary.refresh_end()

    def __init__(self, config):
        """Создание окна с виджетами.
        config - экземпляр Configuration."""

        resldr = get_resource_loader()
        uibldr = resldr.load_gtk_builder('photostat.ui')

        self.config = config
        self.stopScanning = False
        self.progressDelay = self.PROGRESS_DELAY
        self.stats = PhotoStatistics()

        self.window, hdrbar = get_ui_widgets(uibldr,
            'wndMain', 'hdrBar')

        self.window.set_size_request(WIDGET_BASE_WIDTH * 64, WIDGET_BASE_HEIGHT * 25)

        hdrbar.set_title(APP_TITLE)
        hdrbar.set_subtitle('v%s' % APP_VERSION)

        self.window.set_icon(resldr.load_pixbuf_icon_size('photostat.svg', Gtk.IconSize.DIALOG))

        # делаем страницы визарда наполовину вручную - потому что Gtk.Assistant попросту уёбищен
        self.pages = uibldr.get_object('pages')

        #
        # кнопки
        #
        self.btnNextPage, self.btnResultCopy, self.btnResultSave = get_ui_widgets(uibldr,
            'btnNextPage', 'btnResultCopy', 'btnResultSave')

        self.imgStart = Gtk.Image.new_from_icon_name('system-run-symbolic', Gtk.IconSize.BUTTON)
        self.imgStop = Gtk.Image.new_from_icon_name('media-playback-stop-symbolic', Gtk.IconSize.BUTTON)
        self.imgHome = Gtk.Image.new_from_icon_name('go-home-symbolic', Gtk.IconSize.BUTTON)

        #
        # Страница 1: выбор каталога и типов файлов
        #

        self.fcbtnPicDir = uibldr.get_object('fcbtnPicDir')
        self.fcbtnPicDir.select_filename(self.config.cfgPhotoRootDir)

        #
        # Страница 2: сбор статистики
        #

        self.txtProgress, self.progressBar = get_ui_widgets(uibldr,
            'txtProgress', 'progressBar')

        #
        # Страница 3: отображение статистики
        #

        self.faSummary = TreeViewShell.new_from_uibuilder(uibldr, 'tvFASummary')

        # сохранение статистики

        #
        #
        #
        self.curPage = self.PAGE_START
        self.pages.set_current_page(self.curPage)

        self.window.show_all()

        self.setup_sensitive_widgets()

        uibldr.connect_signals(self)

    def btnAbout_clicked(self, btn):
        AboutDialog(self.window).run()

    def btnStart_clicked(self, btn):
        self.select_next_page(True)

    def btnResultCopy_clicked(self, btn):
        self.copy_stat_to_clipboard()

    def btnResultSave_clicked(self, btn):
        self.save_stat_to_file()

    def pages_switch_page(self, nb, page, pagenum):
        self.curPage = pagenum
        self.setup_sensitive_widgets()

    def fcbtnPicDir_selection_changed(self, fc):
        # выбран корневой каталог фотопомойки
        self.config.cfgPhotoRootDir = self.fcbtnPicDir.get_filename()
        self.setup_sensitive_widgets()

    def setup_sensitive_widgets(self):
        cadd = 'suggested-action'
        cremove = 'destructive-action'

        if self.curPage == self.PAGE_START:
            bStart = bool(self.config.cfgPhotoRootDir)
            bSave = False
            img = self.imgStart
        elif self.curPage == self.PAGE_PROGRESS:
            bStart = True
            bSave = False
            img = self.imgStop
            cadd, cremove = cremove, cadd
        else:
            # self.PAGE_RESULT
            bStart = True
            bSave = True
            img = self.imgHome

        self.btnNextPage.set_sensitive(bStart)
        self.btnNextPage.set_image(img)

        sc = self.btnNextPage.get_style_context()
        sc.remove_class(cremove)
        sc.add_class(cadd)

        self.btnResultCopy.set_sensitive(bSave)
        self.btnResultSave.set_sensitive(bSave)

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
                    f.write(str(self.stats.get_stat_table()))
            except Exception as ex:
                msg_dialog(self.window, 'Сохранение статистики в файл',
                               'Не удалось сохранить файл.\n%s' % exception_to_str(ex))

    def copy_stat_to_clipboard(self):
        try:
            cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            cb.clear()
            cb.set_text(str(self.stats.get_stat_table()), -1)
            cb.store()
        except Exception as ex:
            msg_dialog(self.window, 'Копирование статистики в буфер обмена',
                           'Сбой при операции с буфером обмена - %s' % exception_to_str(ex))

    def main(self):
        Gtk.main()


def save_load_settings(config, save):
    e = config.save() if save else config.load()

    if e:
        msg_dialog(None, '%s - %s настроек' % (APP_TITLE, 'сохранение' if save else'загрузка'),
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
