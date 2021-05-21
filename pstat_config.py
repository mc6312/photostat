#!/usr/bin/env python3
# -*- coding: utf-8 -*-


""" pstat_config.py

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


import os.path
from configparser import ConfigParser
from platform import system as get_system_name
import sys
from collections import namedtuple


from pstat_common import *


# список расширений файлов
IMAGE_FILE_EXTS = set(['jpg', 'jpeg', 'tif', 'tiff', 'png'])
RAW_FILE_EXTS   = set(('3fr', 'ari', 'arw', 'srf', 'sr2',
    'bay', 'braw', 'cri', 'crw', 'cr2', 'cr3', 'cap', 'iiq',
    'eip', 'dcs', 'dcr', 'drf', 'k25', 'kdc', 'dng', 'erf',
    'fff', 'gpr', 'mef', 'mdc', 'mos', 'mrw', 'nef', 'nrw', 'orf', 'pef', 'ptx', 'pxn',
   'r3d', 'raf', 'raw', 'rw2', 'rwl', 'rwz', 'srw', 'x3f'))




class Configuration():
    CS_SETTINGS = 'settings'
    CV_PHOTO_ROOT_DIR = 'photo_root_dir'
    CV_STAT_SAVE_FILE = 'stat_save_file'
    CV_SCAN_RAW_FILES = 'scan_raw_files'
    CV_SCAN_IMAGE_FILES = 'scan_image_files'
    CV_RAW_FILE_EXTS = 'raw_file_extensions'
    CV_IMAGE_FILE_EXTENSIONS = 'image_file_extensions'

    DEF_PHOTO_ROOT_DIR = os.path.expanduser('~')
    DEF_STAT_SAVE_DIR = os.path.expanduser('~/photo-statistics.txt')
    DEF_SCAN_RAW_FILES = True
    DEF_SCAN_IMAGE_FILES = False

    def __init__(self, fname):
        """Первоначальная инициализация настроек значениями по умолчанию.
        fname - имя файла, откуда будут загружаться и куда будут сохраняться
        настройки."""

        self.cfgFN = fname

        self.cfgPhotoRootDir = self.DEF_PHOTO_ROOT_DIR
        self.cfgStatSaveFile = self.DEF_STAT_SAVE_DIR

        self.cfgScanRAWfiles = self.DEF_SCAN_RAW_FILES
        self.cfgScanImageFiles = self.DEF_SCAN_IMAGE_FILES

        self.cfgRAWFileExtensions = RAW_FILE_EXTS
        self.cfgImageFileExtensions = IMAGE_FILE_EXTS

    def __str__(self):
        return '''self.cfgFN = '%s'
self.cfgPhotoRootDir = '%s'
self.cfgStatSaveFile = '%s'
self.cfgScanRAWfiles = %s
self.cfgScanImageFiles = %s
self.cfgRAWFileExtensions = %s
self.cfgImageFileExtensions = %s''' % (self.cfgFN,
            self.cfgPhotoRootDir,
            self.cfgStatSaveFile,
            self.cfgScanRAWfiles,
            self.cfgScanImageFiles,
            self.cfgRAWFileExtensions,
            self.cfgImageFileExtensions)

    def load(self):
        """Загрузка пользовательских настроек.
        В случае успеха возвращает None, в случае ошибки - строку
        с сообщением об ошибке.
        Отсутствие файла с настройками ошибкой не считается."""

        cfg = ConfigParser()

        if os.path.exists(self.cfgFN):
            try:
                with open(self.cfgFN, 'r') as f:
                    cfg.read_file(f, self.cfgFN)

            except Exception as ex:
                return 'Ошибка загрузки настроек - %s' % exception_to_str(ex)

        self.cfgPhotoRootDir = os.path.abspath(cfg.get(self.CS_SETTINGS, self.CV_PHOTO_ROOT_DIR, fallback=self.DEF_PHOTO_ROOT_DIR))
        self.cfgStatSaveFile = os.path.abspath(cfg.get(self.CS_SETTINGS, self.CV_STAT_SAVE_FILE, fallback=self.DEF_STAT_SAVE_DIR))

        self.cfgScanRAWfiles = cfg.getboolean(self.CS_SETTINGS, self.CV_SCAN_RAW_FILES, fallback=self.DEF_SCAN_RAW_FILES)
        self.cfgScanImageFiles = cfg.getboolean(self.CS_SETTINGS, self.CV_SCAN_IMAGE_FILES, fallback=self.DEF_SCAN_IMAGE_FILES)

        def get_set_of_str(section, option, defval):
            sv = cfg.get(section, option, fallback=None)

            if not isinstance(sv, str):
                return defval

            return set(sv.lower().split(None))

        self.cfgRAWFileExtensions = get_set_of_str(self.CS_SETTINGS, self.CV_RAW_FILE_EXTS, RAW_FILE_EXTS)
        self.cfgImageFileExtensions = get_set_of_str(self.CS_SETTINGS, self.CV_IMAGE_FILE_EXTENSIONS, IMAGE_FILE_EXTS)

    def save(self):
        """Сохранение пользовательских настроек.
        В случае успеха возвращает None, в случае ошибки - строку
        с сообщением об ошибке.
        При необходимости создаёт каталог для файла настроек."""

        cfgDir = os.path.split(self.cfgFN)[0]
        if not os.path.exists(cfgDir):
            try:
                os.makedirs(cfgDir, exist_ok=True)
            except OSError as ex:
                return 'Не удалось создать каталог "%s" - %s' % (cfgDir, exception_to_str(ex))

        cfg = ConfigParser()
        cfg.add_section(self.CS_SETTINGS)

        cfg.set(self.CS_SETTINGS, self.CV_PHOTO_ROOT_DIR, self.cfgPhotoRootDir)
        cfg.set(self.CS_SETTINGS, self.CV_STAT_SAVE_FILE, self.cfgStatSaveFile)

        cfg.set(self.CS_SETTINGS, self.CV_SCAN_RAW_FILES, str(self.cfgScanRAWfiles))
        cfg.set(self.CS_SETTINGS, self.CV_SCAN_IMAGE_FILES, str(self.cfgScanImageFiles))

        def set_set_of_str(section, option, v):
            cfg.set(section, option, ' '.join(sorted(v)))

        set_set_of_str(self.CS_SETTINGS, self.CV_RAW_FILE_EXTS, self.cfgRAWFileExtensions)
        set_set_of_str(self.CS_SETTINGS, self.CV_IMAGE_FILE_EXTENSIONS, self.cfgImageFileExtensions)

        try:
            with open(self.cfgFN, 'w+') as f:
                cfg.write(f)
        except Exception as ex:
                return 'Не удалось сохранить файл настроек "%s" - %s' % (cfgFN, exception_to_str(ex))

    def check_fields(self):
        """Проверка правильности заполнения полей.
        Возвращает булевское значение."""

        if not self.cfgPhotoRootDir or not os.path.isdir(self.cfgPhotoRootDir):
            return False

        if not self.cfgScanRAWfiles and not self.cfgScanImageFiles:
            return False

        return True


def get_config_file_name():
    """Возвращает полный путь к файлу настроек."""

    sysname = get_system_name()

    CFGSUBDIR = 'photostat'

    if sysname == 'Windows':
        cfgDir = os.environ['APPDATA']
    else:
        if sysname != 'Linux':
            print('Внимание! Запуск из неподдерживаемой ОС!', file=sys.stderr)

        cfgDir = os.path.expanduser(u'~/.config')

    return os.path.join(cfgDir, CFGSUBDIR, 'settings.cfg')


def get_resource_directory():
    """Возвращает полный путь к каталогу неизменяемых данных программы."""

    # пока что ищем данные в том же каталоге, где сама программа
    # иначе пришлось бы городить пакеты для линухов, класть файлы
    # в стандартные места и т.п, а также громоздить установщик для винды

    appDir = os.path.split(os.path.abspath(__file__))[0]
    if not os.path.isdir(appDir):
        # похоже, мы в жо... в зипе
        appDir = os.path.split(appDir)[0]

    return appDir


resource_paths = namedtuple('resource_paths', 'logotype license')
# logotype  - путь к файлу с изображением логотипа (иконы) приложения
# license   - путь к файлу лицензии (в данном случае COPYING с GPL v3 внутре)
# если в соотв. поле None или пустая строка - соотв. файл не найден


def get_resource_paths():
    """Возвращает экземпляр resource_paths."""

    resDir = get_resource_directory()

    def check_file_path(fname):
        path = os.path.join(resDir, fname)

        return path if os.path.exists(path) else None

    return resource_paths(check_file_path('photostat.svg'), # да, всё приколочено гвоздями
                          check_file_path('COPYING'))


resourcePaths = get_resource_paths()


if __name__ == '__main__':
    #print(resourcePaths)
    #exit(0)

    cfp = get_config_file_name()
    print(cfp)

    sets = Configuration(cfp)
    e = sets.load()

    if e:
        print('* Error:', e)
    else:
        print(sets)

    #sets.save()
