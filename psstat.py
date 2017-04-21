#!/usr/bin/env python
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


from gi import require_version as gi_require_version
gi_require_version('GExiv2', '0.10') # только чтоб не лаялось...
from gi.repository import GExiv2

GExiv2.log_set_level(GExiv2.LogLevel.MUTE)

import os, os.path
from fractions import Fraction

import psconfig

from warnings import warn


# "служебные" значения для ФР и диафрагмы
# (для сортировки и отображения)
V_UNKNOWN = -1  # для неизвестных значений ФР и диафрагмы;
V_OTHERS = 0    # для группировки строк/столбцов, в которых
                # суммарное значение меньше определенной величины


def normalized_aperture(raperture):
    """Преобразует значение raperture (fractions.Fraction)
    в целое число с фиксированной точкой."""

    f = int(round(raperture) * 10)
    if f <= 0:
        f = V_UNKNOWN

    return f


def normalized_focal_length(fl):
    return V_UNKNOWN if fl <= 0 else fl


class ApertureStatistics():
    def __init__(self, raperture):
        # aperture - значение типа fractions.Fraction

        self.value = float(raperture)

        # для отображения
        self.display = '%g' % self.value

        # кол-во снимков
        self.numPhotos = 0

    def __str__(self):
        return 'a=%s: numPhotos=%d' % (self.display, self.numPhotos)


class FocalLengthStatistics():
    def __init__(self, f):
        # фокусное расстояние (НЕ приведённое к ЭФР!)
        self.focalLength = f

        # всего снимков
        self.totalPhotos = 0

        # словарь, где ключи - нормализованные значения диафрагмы
        # (см. normalized_aperture),
        # а значения - экземпляры ApertureStatistics
        # значение диафрагмы, равное 0, соответствует неизвестному значению
        self.apertures = {}

    def add_photo(self, aperture):
        # aperture - fractions.Fraction
        # возвращает нормализованное значение диафрагмы

        naperture = normalized_aperture(aperture)

        if naperture in self.apertures:
            aobj = self.apertures[naperture]
        else:
            aobj = ApertureStatistics(aperture)
            self.apertures[naperture] = aobj

        aobj.numPhotos += 1

        self.totalPhotos += 1

        return naperture

    def __str__(self):
        return ', '.join(map(lambda k: str(self.apertures[k]), sorted(self.apertures.keys())))


class PhotoStatistics():
    """Статистика по использованным фокусным расстояниям и диафрагмам.

    Порядок операций:
    1. Создание экземпляра класса (или вызов метода clear() существующего
       экземпляра).
    2. Вызов метода scan_directory() (или несколько вызовов для разных
       несовпадающих каталогов.
    3. Вызов метода get_stat_table() для получения финального результата.

    Также см. описания методов."""

    def __init__(self):
        # ключи - фокусные расстояния, значения - экземпляры FocalLengthStatistics
        self.statFocals = {}

        # ключи - нормализованные значения диафрагмы (см. normalized_aperture),
        # значения - экземпляры ApertureStatistics
        self.statApertures = {}

        # общее кол-во снимков
        self.statTotalPhotos = 0

        # кол-во снимков с известными ФР (т.е. у которых EXIF содержит поле ФР)
        self.statKnownFocals = 0

        # общее количество просмотренных файлов
        self.statTotalFiles = 0

    def clear(self):
        """Сброс статистики (перед повторным сбором)."""

        self.statFocals.clear()
        self.statApertures.clear()
        self.statTotalPhotos = 0
        self.statKnownFocals = 0
        self.statTotalFiles = 0

    def scan_directory(self, rootdir, ftypes, callback=None):
        """Ковыряем каталог rootdir на предмет корпстинок и сбора статистики.
        Возвращает None или пустую строку в случае успеха,
        строку с сообщением об ошибке в случае ошибки.

        ftypes - множество (set) допустимых расширений имен файлов

        callback - функция или метод класса, получает два параметра:
            экземпляр класса PhotoStatistics (т.е. self),
            полный путь файла;
        возвращает булевское значение:
            True - перейти к следующему файлу,
            False - прервать работу."""

        def __scan_file(fpath):
            self.statTotalFiles += 1

            fext = os.path.splitext(fname)[1].lower()
            if fext:
                fext = fext[1:] # ибо точку нам не надо

            if fext not in ftypes:
                return

            try:
                gmd = GExiv2.Metadata(fpath)

            except Exception as ex:
                # файлы, которые не содержат EXIF или не открываются
                # выгребалкой по любой другой причине - фотками не считаются.
                # подробности мну в данный момент не колышут.
                #print(ex)
                return

            if not gmd.has_exif():
                # такие товарищи нам совсем не товарищи
                return

            focal = int(round(gmd.get_focal_length()))
            # дробные значения ФР нам нафиг не нужны

            aperture = gmd.get_exif_tag_rational('Exif.Photo.FNumber')
            if not aperture:
                aperture = gmd.get_exif_tag_rational('Exif.Image.FNumber')

            if not aperture or float(aperture) < 0.5:
                # считается, что диафрагмы < 0.7 не бывает, но оставим всё ж запас ради параноищи
                # если вернуло кривое значение (например, <0)
                # считаем это "неизвестным значением"
                aperture = Fraction.from_float(V_UNKNOWN)

            # снимки с EXIF, но с нулевыми значениями ФР и диафрагмы могут быть, например,
            # с нечипованных древних объективов

            # валим в статистику
            if focal in self.statFocals:
                focobj = self.statFocals[focal]
            else:
                focobj = FocalLengthStatistics(focal)
                self.statFocals[focal] = focobj

            naperture = focobj.add_photo(aperture)

            if naperture in self.statApertures:
                aobj = self.statApertures[naperture]
            else:
                aobj = ApertureStatistics(aperture)
                self.statApertures[naperture] = aobj

            aobj.numPhotos += 1

            self.statKnownFocals += 1

            #f35 = gmd.get_tag_long('Exif.Photo.FocalLengthIn35mmFilm')
            #f35 = gmd.get_tag_interpreted_string('Exif.Photo.FocalLengthIn35mmFilm')
            #print('%s ЭФР: %s' % (imgfilename, f35))

            self.statTotalPhotos += 1

        if not os.path.exists(rootdir):
            return 'Каталог "%s" не существует или недоступен' % rootdir

        for root, dirs, files in os.walk(rootdir):
            for fname in files:
                fpath = os.path.join(root, fname)

                __scan_file(fpath)

                # callback вызываем в последнюю очередь, дабы оно
                # при желании могло показать текущее кол-во снимков и т.п.
                if callable(callback) and not callback(self, fpath):
                    return

    class StatTable():
        """Вспомогательный класс для хранения сформированной таблицы
        статистики.
        Не является потомком питоньего класса-списка, дабы не рисковать
        совпадениями имен полей и т.п.

        Поле rows - список списков с данными статистики (ибо глупый питон
        не умеет двумерных массивов без дополнительного шаманства).
        Поле заполняется значениями 'снаружи' - этот класс сам ничего
        не умеет, кроме преобразования своего содержимого в строку.

        В столбцах - диафрагмы, в строках - фокусные расстояния.
        В ячейках - кол-во снимков для соотв. фокусного и диафрагмы.
        Первый столбец - заголовки строк, первая строка - заголовки столбцов.
        Последний столбец и последняя строка - суммарные значения."""

        COL_SEPARATOR = '  '

        def __init__(self):
            self.rows = []

        def clear(self):
            self.rows.clear()

        def __str__(self):
            """Форматирование статистики как текста,
            для сохранения в файл и т.п.

            Если таблица пустая, возвращает пустую строку."""

            ret = []

            if self.rows:
                colWidths = [0] * len(self.rows[0])

                # преобразуем в строки и меряем ширину

                for row in self.rows:
                    for colix, col in enumerate(row):
                        sv = str(col)
                        svl = len(sv)

                        if svl > colWidths[colix]:
                            colWidths[colix] = svl

                        row[colix] = sv

                #print(stat)
                # форматируем

                col0width = colWidths[0]
                del colWidths[0]

                for row in self.rows:
                    srow = self.COL_SEPARATOR.join(map(lambda c: row[c[0] + 1].rjust(c[1], ' '), enumerate(colWidths)))

                    ret.append('%s%s%s' % (row[0].ljust(col0width, ' '), self.COL_SEPARATOR, srow))

            return '\n'.join(ret)

    TABLE_MIN_ROW_THRESHOLD = 2 # порог (в процентах), ниже которого строки таблицы объединяются в строку с заголовком "прочие"

    def get_stat_table(self, reduceRows=True, reduceCols=True):
        """Получение результата после сбора статистики.

        reduceRows - если True - группировать в строку "прочие" строки,
                     в которых суммарное кол-во снимков меньше порога;
        reduceCols - если True - группировать в столбец "прочие" столбцы,
                     в которых суммарное кол-во снимков меньше порога.

        Возвращает экземпляр класса PhotoStatistics.StatTable."""

        S_TOTAL = 'Всего'
        S_UNK = 'неизв.'
        S_OTHER = 'прочие'

        tableMinThreshold = int(self.statTotalPhotos * self.TABLE_MIN_ROW_THRESHOLD / 100)

        #
        # значения диафрагмы - столбцы
        #

        # нормализованные значения диафрагм - ключи для столбцов
        allApertures = set(self.statApertures.keys())
        otherApertures = set()

        # фильтруем данные, группируя малозначимые столбцы
        if reduceCols:
            #!!!
            warn('%s.get_stat_table(): группировка столбцов не реализована!' % self.__class__.__name__)

            if otherApertures:
                allApertures -= otherApertures

        usedApertures = list(sorted(allApertures))

        def disp_ap(nap):
            ap = self.statApertures[nap]

            return S_UNK if nap == V_UNKNOWN else S_OTHER if nap == V_OTHERS else'f/%s' % ap.display

        colHeaders = ['ФР/Д'] + list(map(disp_ap, usedApertures))
        colHeaders += [S_TOTAL]

        # соответствие "диафрагма - столбец", с учетом столбца - заголовка строк
        apertureColumns = dict(map(lambda t: (t[1], t[0] + 1), enumerate(usedApertures)))

        numCols = len(colHeaders)
        numDataCols = len(usedApertures)

        table = self.StatTable()
        table.rows.append(colHeaders)

        #
        # фокусные расстояния - строки
        #

        # имеющиеся значения фокусных расстояний
        allFocals = set(self.statFocals.keys())
        otherFocals = set() # ФР, процент снимков с которыми <TABLE_MIN_ROW_THRESHOLD

        # фильтруем данные, группируя малозначимые строки
        if reduceRows:
            for focal in self.statFocals:
                if self.statFocals[focal].totalPhotos < tableMinThreshold:
                    otherFocals.add(focal)

            if otherFocals:
                allFocals -= otherFocals
        #print(otherFocals)

        usedFocals = list(sorted(allFocals))

        rowHeaders = list(map(lambda f: S_UNK if f == 0 else '%d мм' % f, usedFocals))

        # соответствие "ФР - строка", с учетом строки - заголовка столбцов
        focalRows = dict(map(lambda t: (t[1], t[0] + 1), enumerate(usedFocals)))

        # заполняем таблицу значениями

        rowSummary = [0] * (numDataCols)

        for rowix, focal in enumerate(usedFocals):
            row = [rowHeaders[rowix]] + [0] * numDataCols

            rtotal = 0
            focals = self.statFocals[focal]

            for nap in apertureColumns:
                if nap in focals.apertures:
                    colix = apertureColumns[nap]
                    np = focals.apertures[nap].numPhotos
                    row[colix] = np
                    rowSummary[colix - 1] += np

            row.append(focals.totalPhotos)

            table.rows.append(row)

        if otherFocals:
            rowOthers = [0] * (numDataCols)

            totalOthers = 0

            for rowix, focal in enumerate(otherFocals):
                focals = self.statFocals[focal]
                totalOthers += focals.totalPhotos

                for nap in apertureColumns:
                    if nap in focals.apertures:
                        colix = apertureColumns[nap] - 1

                        np = focals.apertures[nap].numPhotos
                        rowOthers[colix] += np
                        rowSummary[colix] += np

            table.rows.append([S_OTHER] + rowOthers + [totalOthers])

        table.rows.append([S_TOTAL] + rowSummary + [sum(rowSummary)])

        return table

    def __str__(self):
        buf = ['statFocals:'] + list(map(lambda k: '  %7s: %s' % ('f=%d' % k, str(self.statFocals[k])), sorted(self.statFocals.keys())))

        buf += ['statApertures:'] + list(map(lambda k: '  %7s: %d' % ('f/%s' % self.statApertures[k].display, self.statApertures[k].numPhotos),
            sorted(self.statApertures.keys())))

        buf.append('statTotalPhotos: %d' % self.statTotalPhotos)
        buf.append('statKnownFocals: %d' % self.statKnownFocals)
        buf.append('statTotalFiles:  %d' % self.statTotalFiles)

        return '\n'.join(buf)


def __dbg_scan_cbk(statobj, fpath):
    #print(fpath)
    return True


if __name__ == '__main__':
    #PHOTODIR = '~/photos.current'
    PHOTODIR = '~/docs-private/photos/'

    stats = PhotoStatistics()
    e = stats.scan_directory(os.path.expanduser(PHOTODIR), psconfig.RAW_FILE_EXTS, __dbg_scan_cbk)
    if e:
        print('Ошибка: %s' % e)
        exit(1)

    #print(stats)

    stattab = stats.get_stat_table()#reduceRows=False)
    print(stattab)
    print('\nВсего файлов: %d' % stats.statTotalFiles)
    #print('\nСтатистика:')
    #print(stats.format_statistics_str())
