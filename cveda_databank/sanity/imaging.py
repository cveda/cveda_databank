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

import os
from zipfile import ZipFile
try:
    from zipfile import BadZipFile
except ImportError:
    from zipfile import BadZipfile as BadZipFile  # Python 2

import logging
logger = logging.getLogger(__name__)

# import ../../databank
try:
    from .. core import PSC2_FROM_PSC1
    from .. core import Error
except:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), u'../..'))
    from cveda_databank import PSC2_FROM_PSC1
    from cveda_databank import Error


def _check_psc1(subject_id, psc1=None, suffix=None):
    """
    """
    if suffix:
        if subject_id.endswith(suffix):
            subject_id = subject_id[:-len(suffix)]
        elif len(subject_id) <= 12 or subject_id.isdigit():
            yield 'PSC1 code "{0}" should end with suffix "{1}"'.format(subject_id, suffix)
    if subject_id.isdigit():
        if len(subject_id) != 12:
            yield 'PSC1 code "{0}" contains {1} digits instead of 12'.format(subject_id, len(subject_id))
    elif len(subject_id) > 12 and subject_id[:12].isdigit() and not subject_id[12].isdigit():
        yield 'PSC1 code "{0}" ends with unexpected suffix "{1}"'.format(subject_id, subject_id[12:])
        subject_id = subject_id[:12]
    if not subject_id.isdigit():
        yield 'PSC1 code "{0}" should contain 12 digits'.format(subject_id)
    elif len(subject_id) != 12:
        yield 'PSC1 code "{0}" contains {1} characters instead of 12'.format(subject_id, len(subject_id))
    elif subject_id not in PSC2_FROM_PSC1:
        yield 'PSC1 code "{0}" is not valid'.format(subject_id)
    elif psc1:
        if suffix and psc1.endswith(suffix):
            psc1 = psc1[:-len(suffix)]
        if subject_id != psc1:
            yield'PSC1 code "{0}" was expected to be "{1}"'.format(subject_id, psc1)


def check_zip_name(path, psc1=None, timepoint=None):
    """Check correctness of a ZIP filename.

    Parameters
    ----------
    path : str
        Pathname or filename of the ZIP file.
    psc1 : str, optional
        Expected 12-digit PSC1 code.
    timepoint : str, optional
        Time point identifier, found as a suffix in subject identifiers.

    Returns
    -------
    result: tuple
        In case of errors, return the tuple (psc1, errors) where psc1 is
        a collection of PSC1 codes found in the ZIP file and errors is an
        empty list if the ZIP file passes the check and a list of errors
        otherwise.

    """
    basename = os.path.basename(path)
    if basename.endswith('.zip'):
        subject_id = basename[:-len('.zip')]
        errors = [Error(basename, 'Incorrect ZIP file name: ' + message)
                  for message in _check_psc1(subject_id, psc1, timepoint)]
        return subject_id, errors
    else:
        return None, [Error(basename, 'Not a valid ZIP file name')]


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
    for d, ziptree in ziptree.directories.items():
        for error in _check_empty_files(ziptree):
            yield error


def check_zip_content(path, psc1, sequences, timepoint=None):
    """Rapid sanity check of a ZIP file containing imaging data for a subject.

    Parameters
    ----------
    path : str
        Path name of the ZIP file.
    psc1 : str
        Expected 12-digit PSC1 code.
    sequences : dict
        Which sequences to expect.
    timepoint : str, optional
        Time point identifier, found as a suffix in subject identifiers.

    Returns
    -------
    result: tuple
        In case of errors, return the tuple ([], errors) where errors is
        a list of errors. Oterwise return the tuple (psc1, errors) where psc1
        is a list of dectected PSC1 code and errors is an empty list.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.

    """
    subject_ids = []
    errors = []

    basename = os.path.basename(path)

    # internal check on sequences given as argument
    EXPECTED_SEQUENCES = {
        'T1w',
        'dwi',
        'dwi_rev',
        'rest',
        'FLAIR',
        'T2w',
    }
    for sequence in sequences:
        if sequence not in EXPECTED_SEQUENCES:
            logger.error('Unexpected sequence "{0}"'.format(sequence))
            errors.append(Error(__file__,
                                'INTERNAL ERROR: Unexpected sequence "{0}"'
                                .format(sequence)))

    # is the file empty?
    if os.path.getsize(path) == 0:
        errors.append(Error(basename, 'File is empty'))
        return (psc1, errors)

    # read the ZIP file into a tree structure
    try:
        ziptree = ZipTree.create(path)
    except BadZipFile as e:
        errors.append(Error(basename, 'Cannot unzip: "{0}"'.format(e)))
        return (psc1, errors)

    # check tree structure
    for f, z in ziptree.files.items():
        errors.append(Error(f, 'Unexpected file at the root of the ZIP file'))

    for sequence, status in sequences.items():
        if sequence not in ziptree.directories:
            errors.append(Error(basename,
                                'Sequence "{0}" is missing'
                                .format(sequence)))

    for d, z in ziptree.directories.items():
        if d not in EXPECTED_SEQUENCES:
            errors.append(Error(basename,
                                'Unexpected top-level folder "{0}"'
                                .format(d)))
        elif d not in sequences:
            errors.append(Error(basename,
                                'Sequence "{0}" has not been declared, '
                                'but ZIP file contains folder "{0}"'
                                .format(d)))
        elif sequences[d] == 'Missing':
            errors.append(Error(basename,
                                'Sequence "{0}" has been declared missing, '
                                'but ZIP file contains folder "{0}"'
                                .format(d)))
        else:
            pass  # FIXME: there must be at least a DICOM file, check it!
        errors.extend(_check_empty_files(z))

    return (subject_ids, errors)


def main():
    # wrong names
    ZIPFILE = '/volatile/SANITY/080000188813.zip'
    (psc1, errors) = check_zip_name(ZIPFILE, '010000123456')
    print('✘ ' + ZIPFILE)
    if errors:
        for e in errors:
            print('  ▷ ' + str(e))

    ZIPFILE = '/volatile/SANITY/080000188813FU1.zip'
    (psc1, errors) = check_zip_name(ZIPFILE, '010000123456')
    print('✘ ' + ZIPFILE)
    if errors:
        for e in errors:
            print('  ▷ ' + str(e))

    # correct content
    ZIPFILE = '/volatile/SANITY/cveda_good.zip'
    SEQUENCES = {
        'T1w': 'Good',
        'dwi': 'Bad',
        'dwi_rev': 'Dubious',
        'rest': 'Good',
        'FLAIR': 'Good',
        'T2w': 'Good',
    }
    (psc1, errors) = check_zip_content(ZIPFILE, '080000191816', SEQUENCES)
    print('✔ ' + ZIPFILE)
    if errors:
        for e in errors:
            print('▸ ' + str(e))

    # wrong content
    ZIPFILE = '/volatile/SANITY/cveda_bad.zip'
    SEQUENCES = {
        'T1w': 'Good',
        'dwi': 'Bad',
        'dwi_rev': 'Dubious',
        'rest': 'Good',
        'T2w': 'Missing',
        'BOGUS': 'Missing',
    }
    (psc1, errors) = check_zip_content(ZIPFILE, '080000191816', SEQUENCES)
    print('✘ ' + ZIPFILE)
    if errors:
        for e in errors:
            print('▸ ' + str(e))


if __name__ == '__main__':
    main()
