#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2014-2016 CEA
#
# This software is governed by the CeCILL license under French law and
# abiding by the rules of distribution of free software. You can use, 
# modify and/ or redistribute the software under the terms of the CeCILL
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info". 
#
# As a counterpart to the access to the source code and rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty and the software's author, the holder of the
# economic rights, and the successive licensors have only limited
# liability. 
# 
# In this respect, the user's attention is drawn to the risks associated
# with loading, using, modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean that it is complicated to manipulate, and that also
# therefore means that it is reserved for developers and experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or 
# data to be ensured and, more generally, to use and operate it in the 
# same conditions as regards security. 
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license and that you accept its terms.

import logging
logger = logging.getLogger(__name__)

import os
from zipfile import ZipFile
try:
    from zipfile import BadZipFile
except ImportError:
    from zipfile import BadZipfile as BadZipFile  # Python 2
from zipfile import is_zipfile
from tempfile import TemporaryDirectory

# import ../../databank
try:
    from .. core import PSC2_FROM_PSC1
    from .. core import Error
except:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), u'../..'))
    from databank import PSC2_FROM_PSC1
    from databank import Error


class ZipTree:
    """Node of a tree structure to represent ZipFile contents.

    Attributes
    ----------
    directories : dict
        Dictionnary of subdirectories.
    files : str
        Dictionnary of files under this node.

    """

    def __init__(self, filename=''):
        self.filename = filename
        self.directories = {}
        self.files = {}

    @staticmethod
    def create(path):
        ziptree = ZipTree()
        with ZipFile(path, 'r') as z:
            for zipinfo in z.infolist():
                ziptree._add(zipinfo)
        return ziptree

    def _add(self, zipinfo):
        d = self
        if zipinfo.filename.endswith('/'):  # directory
            parts = zipinfo.filename.rstrip('/').split('/')
            filename = ''
            for part in parts:
                filename += part + '/'
                d = d.directories.setdefault(part, ZipTree(filename))
        else:  # file
            parts = zipinfo.filename.split('/')
            basename = parts.pop()
            for part in parts:
                d = d.directories.setdefault(part, ZipTree())
            if basename not in d.files:
                d.files[basename] = zipinfo
            else:
                raise BadZipFile('duplicate file entry in zipfile')

    def pprint(self, indent=''):
        self._print_children(indent, True)

    def _print_children(self, indent='', last=True):
        directories = list(self.directories.items())
        if directories:
            last_directory = directories.pop()
            for d, ziptree in directories:
                ziptree._print(d, indent, False)
        else:
            last_directory = None
        files = list(self.files.items())
        if files:
            if last_directory:
                d, ziptree = last_directory
                ziptree._print(d, indent, False)
            last_file = files.pop()
            for f, zipinfo in files:
                print(indent + '├── ' + f)
            f, zipinfo = last_file
            print(indent + '└── ' + f)
        elif last_directory:
            d, ziptree = last_directory
            ziptree._print(d, indent, True)

    def _print(self, name, indent='', last=True):
        if last:
            print(indent + '└── ' + name)
            indent += '    '
        else:
            print(indent + '├── ' + name)
            indent += '│   '
        self._print_children(indent, last)


def _check_empty_files(ziptree):
    """Recursively check for empty files in a ZipTree.

    Parameters
    ----------
    ziptree : ZipTree

    Yields
    -------
    error: Error

    """
    for f, zipinfo in ziptree.files.items():
        if zipinfo.file_size == 0:
            yield Error(zipinfo.filename, 'File is empty')
    for d, ziptree in ziptree.directories.values():
        for error in _check_empty_files(ziptree):
            yield error


def _check_image_data(ziptree):
    """Check the "ImageData" folder of a ZipTree.

    Parameters
    ----------
    ziptree : ZipTree
        "ImageData" branch with the meta-data read from the ZIP file.

    Yields
    -------
    error: Error

    """
    if len(ziptree.directories) == 0 and len(ziptree.files) == 0:
        yield Error(ziptree.filename, 'Folder "ImageData" is empty')
    for error in _check_empty_files(ziptree):
        yield error


def _check_ziptree(basename, ziptree):
    """Check the uppermost folder of a ZipTree.

    Parameters
    ----------
    basename : str
        Basename of the ZIP file.

    ziptree : ZipTree
        Meta-data read from the ZIP file.

    Returns
    -------
    result: tuple
        In case of errors, return the tuple (None, errors) where errors is
        a list of errors. Oterwise return the tuple (psc1, errors) where psc1
        is the dectected PSC1 code and errors is an empty list.

    """
    psc1 = []
    errors = []

    if len(ziptree.directories) != 1 or len(ziptree.files) > 0:
        errors.append(Error(basename, 'The ZIP file must contain a single '
                                      'uppermost folder and only that folder'))
    for d, z in ziptree.directories.items():
        # is the name of the uppermost directory a valid PSC1 code?
        if not d.isdigit():
            errors.append(Error(z.filename, 'The name of the uppermost folder "{0}" '
                                            'must be a PSC1 code made of digits'.format(d)))
        elif len(d) != 12:
            errors.append(Error(z.filename, 'The name of the uppermost folder "{0}" contains '
                                            '{1} digits instead of 12'.format(d, len(d))))
        elif d not in PSC2_FROM_PSC1:
            errors.append(Error(z.filename, 'The name of the uppermost folder "{0}" '
                                            'is not a valid PSC1 code'.format(d)))
        else:
            psc1.append(d)
        # ImagingData
        if 'ImageData' in z.directories:
            i = z.directories['ImageData']
            for error in _check_image_data(i):
                errors.append(error)
        else:
            errors.append(Error(z.filename + 'ImageData/', 'Folder "ImageData" is missing'))

        return psc1, errors


def check(path):
    """Rapid sanity check of a ZIP file containing imaging data for a subject.

    Parameters
    ----------
    path : str
        Path name to the ZIP file.

    Returns
    -------
    result: tuple
        In case of errors, return the tuple ([], errors) where errors is
        a list of errors. Oterwise return the tuple (psc1, errors) where psc1
        is a liste of dectected PSC1 code and errors is an empty list.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.

    """
    psc1 = []
    errors = []

    basename = os.path.basename(path)

    # is the file empty?
    if os.path.getsize(path) == 0:
        errors.append(Error(basename, 'File is empty'))
        return (psc1, errors)

    # does it look like a ZIP file?
    if not is_zipfile(path):
        errors.append(Error(basename, 'This is not a ZIP file'))
        return (psc1, errors)

    # read the ZIP file into a tree structure
    try:
        ziptree = ZipTree.create(path)
    except BadZipFile as e:
        errors.append(Error(basename, 'Cannot unzip: "{0}"'.format(e)))
        return (psc1, errors)

    # check tree structure
    p, e = _check_ziptree(basename, ziptree)
    psc1.extend(p)
    errors.extend(e)

    return (psc1, errors)


def extended_check(path):
    """Extended sanity check of the contents of a ZIP file.

    Parameters
    ----------
    path : str
        Path name to the ZIP file.

    Returns
    -------
    result: tuple
        In case of errors, return the tuple ([], errors) where errors is
        a list of errors. Oterwise return the tuple (psc1, errors) where psc1
        is a liste of dectected PSC1 code and errors is an empty list.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.

    """
    psc1 = []
    errors = []

    basename = os.path.basename(path)

    with ZipFile(path, 'r') as z:
        with TemporaryDirectory() as root:
            z.extractall(root)
            ### TODO: run dcm2nii on files ###


def main():
    ZIPFILE = '/volatile/test.zip'
    psc1, errors = check(ZIPFILE)
    if errors:
        for e in errors:
            print('▸ ' + str(e))


if __name__ == '__main__':
    main()
