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

    def __scan_progress(self, stats, fraction, message):
        self.progressDelay -= 1
        if self.progressDelay <= 0:
            self.progressDelay = self.PROGRESS_DELAY

            if fraction < 0.0:
                self.progressBar.pulse()
            else:
                self.progressBar.set_fraction(fraction)

            self.txtProgress.set_text(message)

        flush_gtk_events()

        return not self.stopScanning

    def __scan_stage(self, msg):
        self.txtProgressStage.set_text(msg)
        flush_gtk_events()

    def scan_photos(self):
        try:
            nextPage = self.PAGE_RESULT
            self.stopScanning = False
            self.progressDelay = self.PROGRESS_DELAY

            self.stats.clear()

            ftypes = set()

            if self.config.cfgScanRAWFiles:
                ftypes.update(RAW_FILE_EXTS)

            if self.config.cfgScanImageFiles:
                ftypes.update(IMAGE_FILE_EXTS)

            try:
                ok, em = self.stats.gather_photo_statistics(self.config.cfgPhotoRootDir,
                    ftypes,
                    self.__scan_stage,
                    self.__scan_progress)
            except Exception as ex:
                dump_exception()
                ok = True
                em = str(ex)

            if em or not ok:
                nextPage = self.PAGE_START

                if em:
                    msg_dialog(self.window, APP_TITLE, em)

        finally:
            self.update_stats_view()
            # принудительно переключаем страницу морды
            self.pages.set_current_page(nextPage)

    def select_next_page(self):
        """Реакция на кнопку/пункт меню *NextPage - переход на следующую
        стадию процесса в зависимости от текущей."""

        if self.curPage == self.PAGE_START:
            # запуск сбора данных
            nextPage = self.PAGE_PROGRESS
        elif self.curPage == self.PAGE_PROGRESS:
            # остановка сбора данных, возврат на начальную страницу
            self.stopScanning = True
            nextPage = self.PAGE_START
        else:
            # возврат на начальную страницу
            nextPage = self.PAGE_START

        self.pages.set_current_page(nextPage)

        if nextPage == self.PAGE_PROGRESS:
            self.scan_photos()

    def update_stats_view(self):
        """Обновление отображалки статистики"""

        # чистим отображало от старых настроек и значений
        self.statViewFA.refresh_begin()
        # т.к. ниже будем создавать новый экземпляр Gtk.ListStore
        self.statViewFA.store = None

        while self.statViewFA.view.get_n_columns() > 0:
            self.statViewFA.view.remove_column(self.statViewFA.view.get_column(0))

        # это дерево только чистим - кол-во столбцов в нём не изменяется
        self.statViewByYear.refresh_begin()

        # тут тоже только чистим
        self.statViewByISO.refresh_begin()

        # таблицу статистики по годам получаем, но не используем -
        # для Gtk.TreeStore нужны исходные данные из stats
        statFA = self.stats.get_stat_table_by_focals()

        #
        # статистика по фокусным/диафрагмам
        #
        if statFA.rows:
            # создаем и засираем новую таблицу
            # 1й столбец - заголовок
            # следующие - пары из строки (для отображения)
            # и целого (для прогрессбара)

            lastcol = len(statFA.rows[0]) - 1

            coltypes = [GObject.TYPE_STRING] + [GObject.TYPE_STRING, GObject.TYPE_INT] * lastcol

            self.statViewFA.store = Gtk.ListStore(*coltypes)

            self.statViewFA.view.append_column(Gtk.TreeViewColumn(statFA.rows[0][0], Gtk.CellRendererText(), text=0))

            crpb = Gtk.CellRendererProgress()
            crpb.set_property('text-xalign', 0.0)

            for ixcol in range(lastcol):
                dcol = 1 + (ixcol * 2)
                col = Gtk.TreeViewColumn(statFA.rows[0][ixcol + 1], crpb, text=dcol, value=dcol + 1)
                col.set_expand(True)
                self.statViewFA.view.append_column(col)

            # заполняем данными
            for rowix in range(1, len(statFA.rows)):
                row = statFA.rows[rowix]

                strow = [row[0]]
                for col in row[1:]:
                    # пара значений - строка для отображения
                    strow.append(str(col) if col > 0 else '')

                    # и значение для прогрессбара
                    p = 0 if self.stats.statTotalPhotos == 0 else col * 100 / self.stats.statTotalPhotos

                    strow.append(p)

                self.statViewFA.store.append(strow)

        #
        # статистика по годам
        #
        for yearno, year in sorted(self.stats.statByYear.items()):
            # номер года и кол-во снимков за год
            ytotal = year[0]

            # здесь и далее: в строку преобразуем только те значения,
            # которые не должны быть преобразованы в StatTable.__str__()
            pcs = 100.0 * ytotal / self.stats.statByYearTotal
            # здесь и далее: а какого хрена у Gtk.ProgressBar
            # значение называется fraction, типа float в диапазоне 0..1,
            # а у CellRendererProgress - value, int в диапазоне 0..100?
            itr = self.statViewByYear.store.append(None,
                (str(yearno), str(ytotal), pcs, '%.1f%%' % pcs))

            # по месяцам, за исключением нулевого (суммы за год)
            months = set(year.keys()) - {0}
            for month in sorted(months):
                np = year[month]
                pcs = 100.0 * np / ytotal
                self.statViewByYear.store.append(itr,
                    (self.stats.MONTH_STR[month - 1], str(np), pcs, '%.1f%%' % pcs))

        #
        # по значениям ISO Speed
        #
        for isoSpeed, nPhotos in sorted(self.stats.statByISOSpeed.items()):
            self.statViewByISO.store.append((str(isoSpeed),
                percents_str(nPhotos, self.stats.statByISOSpeedTotal),
                str(nPhotos),
                100.0 * nPhotos / self.stats.statByISOSpeedTotal))
        #
        self.statViewByISO.refresh_end()
        self.statViewByYear.refresh_end()
        self.statViewByYear.view.expand_all()
        self.statViewFA.refresh_end()

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

        self.window.set_size_request(WIDGET_BASE_WIDTH * 80, WIDGET_BASE_HEIGHT * 40)

        hdrbar.set_title(APP_TITLE)
        hdrbar.set_subtitle('v%s' % APP_VERSION)

        self.window.set_icon(resldr.load_pixbuf_icon_size('photostat.svg', Gtk.IconSize.DIALOG))

        # делаем страницы визарда наполовину вручную - потому что Gtk.Assistant попросту уёбищен
        self.pages = uibldr.get_object('pages')

        #
        # кнопки
        #
        self.btnNextPage, self.mnuNextPage, self.btnResultCopy, self.btnResultSave = get_ui_widgets(uibldr,
            'btnNextPage', 'mnuNextPage', 'btnResultCopy', 'btnResultSave')

        self.imgStart = Gtk.Image.new_from_icon_name('system-run-symbolic', Gtk.IconSize.BUTTON)
        self.imgStop = Gtk.Image.new_from_icon_name('media-playback-stop-symbolic', Gtk.IconSize.BUTTON)
        self.imgHome = Gtk.Image.new_from_icon_name('go-home-symbolic', Gtk.IconSize.BUTTON)

        #
        # Страница 1: выбор каталога и типов файлов
        #

        self.fcbtnPicDir, self.chkScanImageFiles, self.chkScanRAWFiles = get_ui_widgets(uibldr,
            'fcbtnPicDir', 'chkScanImageFiles', 'chkScanRAWFiles')

        self.chkScanImageFiles.set_active(self.config.cfgScanImageFiles)
        self.chkScanRAWFiles.set_active(self.config.cfgScanRAWFiles)

        self.fcbtnPicDir.select_filename(self.config.cfgPhotoRootDir)

        #
        # Страница 2: сбор статистики
        #

        self.txtProgress, self.txtProgressStage, self.progressBar = get_ui_widgets(uibldr,
            'txtProgress', 'txtProgressStage', 'progressBar')

        #
        # Страница 3: отображение статистики
        #

        self.statViewFA = TreeViewShell.new_from_uibuilder(uibldr, 'tvFASummary')
        self.statViewByYear = TreeViewShell.new_from_uibuilder(uibldr, 'tvStatByYear')
        self.statViewByISO = TreeViewShell.new_from_uibuilder(uibldr, 'tvStatByISO')

        # сохранение статистики

        # т.к. Glade текущей версии (3.38.2) с какого-то перепугу
        # не умеет создавать
        # а) диалоги _сохранения_ (только открытия файлов и выбора каталога)
        # б) не умеет пихать стандартные кнопки диалогов в ихий же HeaderBar
        # создаём диалог тупо вручную

        self.dlgSaveAs = Gtk.FileChooserDialog()
        self.dlgSaveAs.set_title('Выбор файла для сохранения статистики')
        self.dlgSaveAs.set_action(Gtk.FileChooserAction.SAVE)
        self.dlgSaveAs.set_do_overwrite_confirmation(True)

        self.dlgSaveAs.add_buttons('Отмена', Gtk.ResponseType.CANCEL,
            'OK', Gtk.ResponseType.OK)
        self.dlgSaveAs.set_default_response(Gtk.ResponseType.OK)

        for fltname, fltpat in (('Текстовые файлы', '*.txt'), ('Все файлы', '*.*')):
                fltr = Gtk.FileFilter()
                fltr.set_name(fltname)
                fltr.add_pattern(fltpat)
                self.dlgSaveAs.add_filter(fltr)
        #
        #
        #
        self.curPage = self.PAGE_START
        self.pages.set_current_page(self.curPage)

        self.window.show_all()

        self.setup_sensitive_widgets()

        uibldr.connect_signals(self)

    def chkScanImageFiles_toggled(self, cbtn):
        self.config.cfgScanImageFiles = cbtn.get_active()

    def chkScanRAWFiles_toggled(self, cbtn):
        self.config.cfgScanRAWFiles = cbtn.get_active()

    def btnAbout_clicked(self, btn):
        AboutDialog(self.window).run()

    def btnNextPage_clicked(self, btn):
        self.select_next_page()

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
            txt = 'Собрать статистику'
        elif self.curPage == self.PAGE_PROGRESS:
            bStart = True
            bSave = False
            img = self.imgStop
            txt = 'Прекратить сбор статистики'
            cadd, cremove = cremove, cadd
        else:
            # self.PAGE_RESULT
            bStart = True
            bSave = True
            txt = 'Начать сначала'
            img = self.imgHome

        self.btnNextPage.set_sensitive(bStart)
        self.btnNextPage.set_image(img)
        self.mnuNextPage.set_label(txt)

        sc = self.btnNextPage.get_style_context()
        sc.remove_class(cremove)
        sc.add_class(cadd)

        self.btnResultCopy.set_sensitive(bSave)
        self.btnResultSave.set_sensitive(bSave)

    def save_stat_to_file(self):
        self.dlgSaveAs.select_filename(self.config.cfgStatSaveFile)

        self.dlgSaveAs.show()
        r = self.dlgSaveAs.run()
        self.dlgSaveAs.hide()

        if r == Gtk.ResponseType.OK:
            self.config.cfgStatSaveFile = self.dlgSaveAs.get_filename()
            try:
                with open(self.config.cfgStatSaveFile, 'w+') as f:
                    f.write(self.stats.get_stat_tables_str())
            except Exception as ex:
                msg_dialog(self.window, 'Сохранение статистики в файл',
                               'Не удалось сохранить файл.\n%s' % exception_to_str(ex))

    def copy_stat_to_clipboard(self):
        try:
            cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            cb.clear()
            cb.set_text(self.stats.get_stat_tables_str(), -1)
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
