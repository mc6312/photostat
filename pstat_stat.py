#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" pstat_stat.py

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


from gi import require_version as gi_require_version
gi_require_version('GExiv2', '0.10') # только чтоб не лаялось...
from gi.repository import GExiv2

GExiv2.log_set_level(GExiv2.LogLevel.MUTE)

import os, os.path
import datetime
from fractions import Fraction

import pstat_config
from pstat_common import *

from warnings import warn


# "служебные" значения для ФР и диафрагмы
# (для сортировки и отображения)
V_UNKNOWN = -1  # для неизвестных значений ФР и диафрагмы;
V_OTHERS = 0    # для группировки строк/столбцов, в которых
                # суммарное значение меньше определенной величины


# коэффициент для преобразования значения диафрагмы
# (fractions.Fraction или float) в целое с фиксированной точкой

APERTURE_NORM_CF = 10.0


def normalized_aperture(raperture):
    """Преобразует значение raperture (fractions.Fraction)
    в целое число с фиксированной точкой."""

    f = int(float(raperture) * APERTURE_NORM_CF)
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

    def __repr__(self):
        return '%s(value=%s, display=%s, numPhotos=%d)' % (self.__class__.__name__,
            self.value, self.display, self.numPhotos)


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

    def __repr__(self):
        return '%s(focalLength=%d, totalPhotos=%d, apertures=%s)' % (self.__class__.__name__,
            self.focalLength,
            self.totalPhotos,
            self.apertures)


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

        # общее кол-во снимков с хоть какими-то метаданными
        self.statTotalPhotos = 0

        # кол-во снимков с известными ФР (т.е. у которых EXIF содержит поле ФР)
        self.statKnownFocals = 0

        # статистика количества снимков по годам:
        # ключи - года, значения - словари,
        # где ключи - месяцы, а значения - счетчики снимков
        # снимки без даты не учитываются
        self.statByYear = {}

        # статистика по значениям ISO
        # ключи - значения ISO Speed, значения - кол-во снимков
        self.statByISOSpeed = {}
        # общее кол-во снимков, где в метаданных указано значение ISO Speed
        self.statByISOSpeedTotal = 0

        # общее количество снимков, где в метаданных указана дата (что не гарантировано)
        # т.е. значение может не совпадать с self.statTotalPhotos
        self.statByYearTotal = 0

        # общее количество просмотренных файлов
        self.statTotalFiles = 0

    def clear(self):
        """Сброс статистики (перед повторным сбором)."""

        self.statTotalPhotos = 0

        self.statFocals.clear()
        self.statApertures.clear()
        self.statKnownFocals = 0

        self.statByYearTotal = 0
        self.statByYear.clear()

        self.statByISOSpeed.clear()
        self.statByISOSpeedTotal = 0

        self.statTotalFiles = 0

    # тэги даты/времени создания снимка в порядке предпочтения
    # (авось хоть какой обнаружится в файле)
    __DT_TAGS = ('Exif.Photo.DateTimeDigitized',
        'Exif.Image.DateTimeOriginal',
        'Exif.Photo.DateTimeOriginal',
        'Exif.Image.DateTime')

    def __process_file_metadata(self, fpath):
        """Извлечение метаданных из файла фотографии и учёт их в статистике."""

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
            # снимки без метаданных не учитываем ваще совсем
            return

        #
        self.statTotalPhotos += 1

        # дробные значения ФР нам нафиг не нужны
        focal = int(round(gmd.get_focal_length()))

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

        # статистика по ISO Speed

        isoSpeed = gmd.get_iso_speed()
        if isoSpeed > 0:
            self.statByISOSpeedTotal += 1

            self.statByISOSpeed[isoSpeed] = self.statByISOSpeed.get(isoSpeed, 0) + 1

        # статистика по ISO Speed и выдержкам
        #print(naperture / APERTURE_NORM_CF, isoSpeed)
        #TODO м.б. сделать статистику по ISO Speed и выдержкам
        #print(gmd.get_exposure_time())

        #
        # определяем дату создания снимка для статистики по годам и месяцам
        #
        year = None
        month = None

        for dtn in self.__DT_TAGS:
            tagv = gmd.get_tag_string(dtn)
            if tagv:
                try:
                    pdate = datetime.datetime.strptime(tagv, '%Y:%m:%d %H:%M:%S').date()
                except:
                    continue

                year = pdate.year
                month = pdate.month
                break

        # пихаем статистику по годам
        if year is None or month is None:
            # снимки без даты не учитываем
            return

        self.statByYearTotal += 1

        # месяцы с номером 0 содержат общее кол-во снимков за соотв. год

        if year in self.statByYear:
            self.statByYear[year][month] = self.statByYear[year].get(month, 0) + 1
            self.statByYear[year][0] = self.statByYear[year].get(0, 0) + 1
        else:
            self.statByYear[year] = {0:1, month:1}

    def gather_photo_statistics(self, photodir, ftypes, stagedisp=None, progressdisp=None):
        """Поиск файлов фотографий и учёт их метаданных.

        Параметры:
            photodir        - строка с путём к каталогу с фотографиями;
            ftypes          - множество (set) допустимых расширений имен файлов
            stagedisp       - функция или метод класса, получает один параметр -
                              строку с названием стадии процесса;
            progressdisp    - функция или метод класса, получает следующие параметры:
                              1: экземпляр класса PhotoStatistics (т.е. self),
                              2: float - значение прогресса;
                                  при значении < 0 прогрессбар отображается
                                  в режиме "пульсации";
                              3: строка с сообщением о деталях процесса (м.б. пустой).
                              Функция должна возвращать булевское значение:
                                True - перейти к следующему файлу,
                                False - прервать работу.

        Возвращает кортеж из двух элементов:
        1. булевское значение - True, если сбор завершен (в т.ч. с ошибкой),
           False, если сбор прерван пользователем;
        2. None или пустая строка, если ошибок не было, или строка
           с сообщением об ошибке."""

        if not os.path.exists(photodir):
            return (True, 'Каталог "%s" не существует или недоступен' % photodir)

        if not callable(progressdisp):
            progressdisp = lambda sobj, fraction, msg: True

        if not callable(stagedisp):
            stagedisp = lambda msg: None

        allFiles = []

        stagedisp('Поиск файлов')

        for root, dirs, files in os.walk(photodir):
            for fname in files:
                fpath = os.path.join(root, fname)

                self.statTotalFiles += 1

                fext = os.path.splitext(fname)[1].lower()

                if fext not in ftypes:
                    continue

                allFiles.append(fpath)

                if not progressdisp(self, -1,
                    'Всего файлов: %d, будет обработано: %d' % (self.statTotalFiles, len(allFiles))):
                    return (False, None)

        nFoundFiles = len(allFiles)

        if nFoundFiles:
            stagedisp('Обработка метаданных')

            for ixFile, fpath in enumerate(allFiles, 1):
                self.__process_file_metadata(fpath)

                if not progressdisp(self, ixFile / nFoundFiles, 'Файл %d из %d' % (ixFile, nFoundFiles)):
                    return (False, None)

        return (True, None)

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
        Подразумевается, что (но не обязательно):
            - первый столбец - заголовки строк, первая строка - заголовки
              столбцов;
            - последний столбец и последняя строка - суммарные значения."""

        COL_SEPARATOR = '  '

        def __init__(self, title):
            self.title = title
            self.rows = []

        def clear(self):
            self.rows.clear()

        def __str__(self):
            """Форматирование статистики как текста,
            для сохранения в файл и т.п.

            Если таблица пустая, возвращает пустую строку."""

            ret = [self.title]

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

    # названия месяцев; пока без учёта локали, а там видно будет
    MONTH_STR = ('январь', 'февраль', 'март', 'апрель',
        'май', 'июнь', 'июль', 'август',
        'сентябрь', 'октябрь', 'ноябрь', 'декабрь')

    def get_stat_table_by_focals(self):
        """Получение результата после сбора статистики:
        таблица статистики по диафрагмам и фокусным расстояниям.
        Возвращает экземпляр класса PhotoStatistics.StatTable"""

        S_TOTAL = 'Всего'
        S_UNK = 'неизв.'
        S_OTHER = 'прочие'

        tableMinThreshold = int(self.statTotalPhotos * self.TABLE_MIN_ROW_THRESHOLD / 100)

        #
        # значения диафрагмы - столбцы
        #

        # нормализованные значения диафрагм - ключи для столбцов
        allApertures = set(self.statApertures.keys())

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

        table = self.StatTable('Статистика по фокусным расстояниям и значениям диафрагмы')
        table.rows.append(colHeaders)

        #
        # фокусные расстояния - строки
        #

        # имеющиеся значения фокусных расстояний
        allFocals = set(self.statFocals.keys())
        otherFocals = set() # ФР, процент снимков с которыми <TABLE_MIN_ROW_THRESHOLD

        # фильтруем данные, группируя малозначимые строки
        for focal in self.statFocals:
            if self.statFocals[focal].totalPhotos < tableMinThreshold:
                otherFocals.add(focal)

        if otherFocals:
            allFocals -= otherFocals

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

    def get_stat_table_by_year(self):
        """Получение таблицы статистики по годам.
        Возвращает экземпляр StatTable."""

        table = self.StatTable('Количество снимков по годам и месяцам')

        for yearno, year in sorted(self.statByYear.items()):
            # номер года и кол-во снимков за год
            ytotal = year[0]

            # здесь и далее: в строку преобразуем только те значения,
            # которые не должны быть преобразованы в StatTable.__str__()
            table.rows.append([str(yearno),
                ytotal,
                percents_str(ytotal, self.statByYearTotal)])

            # по месяцам, за исключением нулевого (суммы за год)
            months = set(year.keys()) - {0}
            for month in sorted(months):
                np = year[month]
                table.rows.append(['  %s' % self.MONTH_STR[month - 1],
                    np,
                    percents_str(np, ytotal)])

        return table

    def get_stat_table_by_iso(self):
        table = self.StatTable('Количество снимков с учётом ISO Speed')

        for isoSpeed, nPhotos in sorted(self.statByISOSpeed.items()):
            table.rows.append([isoSpeed, nPhotos, percents_str(nPhotos, self.statByISOSpeedTotal)])

        return table

    def get_stat_tables_str(self):
        return '\n\n'.join(map(str, (
            self.get_stat_table_by_focals(),
            self.get_stat_table_by_year(),
            self.get_stat_table_by_iso())))

    def __repr__(self):
        return '%s(statTotalPhotos=%d, statFocals=%s, statApertures=%s, statKnownFocals=%d, statByYear=%s, statByYearTotal=%d, statByISOSpeed=%s, statByISOSpeedTotal=%d, statTotalFiles=%d)' % (self.__class__.__name__,
            self.statTotalPhotos,
            self.statFocals,
            self.statApertures,
            self.statKnownFocals,
            self.statByYear,
            self.statByYearTotal,
            self.statByISOSpeed,
            self.statByISOSpeedTotal,
            self.statTotalFiles)


def __test_scan_photos():
    from pstat_config import Configuration, get_config_file_name

    cfg = Configuration(get_config_file_name())
    cfg.load()

    def __progressdisp(statobj, fraction, message):
        if message:
            print(message)

        if fraction < 0.0:
            pass #print('.',)
        else:
            print('%d%%' % int(fraction * 100))

        return True

    def __stagedisp(msg):
        print(msg)

    stats = PhotoStatistics()

    ok, em = stats.gather_photo_statistics(cfg.cfgPhotoRootDir,
        pstat_config.RAW_FILE_EXTS,
        __stagedisp,
        __progressdisp)

    if not ok or em:
        print('Ошибка: %s' % em)
        exit(1)

    print(stats)

    print(stats.get_stat_tables_str())
    print('\nВсего файлов: %d' % stats.statTotalFiles)


if __name__ == '__main__':
    print('[debugging %s]' % __file__)

    __test_scan_photos()
