# -*- coding: utf-8 -*-

# Copyright (c) 2014-2017 CEA
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
import tempfile
import shutil
import unicodedata
from zipfile import ZipFile
try:
    from zipfile import BadZipFile
except ImportError:
    from zipfile import BadZipfile as BadZipFile  # Python 2

import logging
logger = logging.getLogger(__name__)

# import ../../databank
try:
    from ..core import PSC2_FROM_PSC1
    from ..core import Error
    from ..dicom_utils import read_metadata
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), u'../..'))
    from cveda_databank import PSC2_FROM_PSC1
    from cveda_databank import Error
    from cveda_databank import read_metadata


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
            yield 'PSC1 code "{0}" was expected to be "{1}"'.format(subject_id, psc1)


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
                ziptree._add(zipinfo)  # pylint: disable=W0212
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
        self._print_children(indent)

    def _print_children(self, indent=''):
        directories = list(self.directories.items())
        if directories:
            last_directory = directories.pop()
            for d, ziptree in directories:
                ziptree._print(d, indent, False)  # pylint: disable=W0212
        else:
            last_directory = None
        files = list(self.files.items())
        if files:
            if last_directory:
                d, ziptree = last_directory
                ziptree._print(d, indent, False)  # pylint: disable=W0212
            last_file = files.pop()
            for f, dummy_zipinfo in files:
                print(indent + '├── ' + f)
            f, dummy_zipinfo = last_file
            print(indent + '└── ' + f)
        elif last_directory:
            d, ziptree = last_directory
            ziptree._print(d, indent)  # pylint: disable=W0212

    def _print(self, name, indent='', last=True):
        if last:
            print(indent + '└── ' + name)
            indent += '    '
        else:
            print(indent + '├── ' + name)
            indent += '│   '
        self._print_children(indent)


class TemporaryDirectory(object):
    """Backport from Python 3.
    """
    def __init__(self, suffix='', prefix=tempfile.gettempprefix(), dir=None):
        self.pathname = tempfile.mkdtemp(suffix, prefix, dir)

    def __repr__(self):
        return '<{} {!r}>'.format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self.pathname

    def __exit__(self, exc, value, tb):
        shutil.rmtree(self.pathname)


def _files(ziptree):
    """List files in a ZipTree.

    Parameters
    ----------
    ziptree : ZipTree

    Yields
    -------
    f: str

    """
    for f in ziptree.files:
        yield ziptree.filename + f
    for ziptree in ziptree.directories.values():
        for f in _files(ziptree):
            yield f


def _check_empty_files(ziptree):
    """Recursively check for empty files in a ZipTree.

    Parameters
    ----------
    ziptree : ZipTree

    Yields
    -------
    error: Error

    """
    for zipinfo in ziptree.files.values():
        if zipinfo.file_size == 0:
            yield Error(zipinfo.filename, 'File is empty')
    for ziptree in ziptree.directories.values():
        for error in _check_empty_files(ziptree):
            yield error


_SERIES_DESCRIPTION = {
    'CHANDIGARH': {
        'T1w': ['3DT1 weighted volume'],
        'rest': ['Resting state fMRI'],
        'B0_map': ['B0 mapping'],
        'dwi': ['DTI'],
        'dwi_rev': ['DTI-reversed'],
        'FLAIR': ['2D fast FLAIR'],
        'T2w': ['2D T2 weighted'],
    },
    'MYSURU_pilot5': {
        'T1w': ['sT1W_3D_TFE'],
        'rest': ['FE_EPI 160'],
        'B0_map': ['B0 mapping'],
        'dwi': ['DTI_high_32'],
        'dwi_rev': ['DTI (reversed)'],
        'FLAIR': ['FLAIR'],
        'T2w': ['T2W_TSE'],
    },
    'MYSURU_pilot4': {
        'T1w': ['3D T1W'],
        'rest': ['RESTING STATE'],
        'B0_map': ['B0 mapping'],
        'dwi': ['DTI_high_32'],
        'dwi_rev': ['DTI_high_6'],
        'FLAIR': ['FLAIR'],
        'T2w': ['T2W'],
    },
    'MYSURU_pilot3': {
        'T1w': ['sT1W_3D_TFE'],
        'rest': ['FE_EPI 160'],
        'B0_map': ['B0 mapping'],
        'dwi': ['DTI_high_32'],
        'dwi_rev': ['DTI_6'],
        'FLAIR': ['FLAIR'],
        'T2w': ['T2W_TSE'],
    },
    'NIMHANS': {
        'T1w': ['3D T1 WEIGHTED VOLUME', '3D T1 WEIGHTED VOLUME_2'],
        'rest': ['act_RESTING STATE fMRI', 'act_Resting state fMRI'],
        'B0_map': ['B0 MAPPING', 'B 0  MAPPING'],
        'dwi': ['DTI_DFC', 'DTI_DFC_MIX', 'DTI _30_DFC_MIX'],
        'dwi_rev': ['DTI REVERSED_DFC', 'DTI REVERSED_DFC_MIX', 'DTI _6_DFC_MIX'],
        'FLAIR': ['2D FAST FLAIR'],
        'T2w': ['2D T2 WEIGHTED'],
    },
    'NIMHANS_pilot': {
        'T1w': ['t1_mprage_sag'],
        'rest': ['bas_Resting STATE fMRI'],
        'B0_map': ['B 0 _mapping_2mm'],
        'dwi': ['DTI _30_DFC'],
        'dwi_rev': ['DTI _6_DFC'],
        'FLAIR': ['2D FLAIR'],
        'T2w': ['2D T2 TSE'],
    },
}


def _match_series_description(sequence, series_description, center=None):
    _SHORT_SERIES_DESCRIPTION = {}

    if center:
        if center in _SHORT_SERIES_DESCRIPTION:
            series = _SHORT_SERIES_DESCRIPTION[center]
            if sequence in series and series_description in series[sequence]:
                return True
    else:
        for series in _SERIES_DESCRIPTION.values():
            if sequence in series and series_description in series[sequence]:
                return True
    return False


def _filter_non_printable(s):
    non_printable = {
        'Cc',  # Other, control
        'Cf',  # Other, format
        'Cs',  # Other, surrogate
        'Co',  # Other, private use
        'Cn',  # Other, not assigned
    }

    def translate(c):
        if c == '\r':
            return '\\r'
        elif c == '\n':
            return '\\n'
        elif unicodedata.category(c) in non_printable:
            n = ord(c)
            if n <= 0xff:
                return '\\x{0:02x}'.format(n)
            else:
                return '\\u{0:04x}'.format(n)
        else:
            return c

    try:
        return ''.join(translate(c) for c in unicode(s))  # Python 2
    except NameError:
        return ''.join(translate(c) for c in s)


def _check_sequence_content(path, ziptree, sequence, psc1, date):
    """Rapid sanity check of a ZIP subfolder containing an MRI sequence.

    Parameters
    ----------
    path : str
        Path name of the ZIP file.
    ziptree : ZipTree
        Tree under the specific sequence folder.
    sequence : str
        Expected sequence.
    psc1 : str
        Expected 12-digit PSC1 code.
    date : datetime.date
        Expected date of acquisition.

    Returns
    -------
    result: tuple
        In case of errors, return the tuple ([], errors) where errors is
        a list of errors. Oterwise return the tuple (psc1, errors) where psc1
        is a list of dectected PSC1 code and errors is an empty list.

    """
    subject_ids = []
    errors = []

    # check zip tree is not empty and does not contain empty files
    files = list(_files(ziptree))
    if len(files) < 1:
        errors.append(Error(ziptree.filename, 'Folder is empty'))
    else:
        errors.extend(_check_empty_files(ziptree))

        # choose a file from zip tree and check its DICOM tags
        with TemporaryDirectory('cveda') as tempdir:
            for f in files:
                with ZipFile(path, 'r') as z:
                    dicom_file = z.extract(f, tempdir)
                    try:
                        metadata = read_metadata(dicom_file, force=True)
                    except IOError:
                        continue
                    else:
                        series_description = metadata['SeriesDescription']
                        if not _match_series_description(sequence, series_description):
                            errors.append(Error(f, 'Unexpected Series Description: {0}'
                                                   .format(series_description)))
                        if 'PatientID' in metadata:
                            patient_id = metadata['PatientID']
                            if not patient_id:
                                errors.append(Error(f, 'Empty PSC1 code'))
                            elif patient_id != psc1:
                                patient_id = _filter_non_printable(patient_id)
                                errors.append(Error(f, 'Inconsistent PSC1 code: {0}'
                                                       .format(patient_id)))
                        else:
                            errors.append(Error(f, 'Missing PSC1 code'))
                        if 'AcquisitionDate' in metadata:
                            if date:
                                acquisition_date = metadata['AcquisitionDate']
                                if acquisition_date != date:
                                    errors.append(Error(f, 'Inconsistent acquisition date: {0}'
                                                           .format(acquisition_date)))
                        else:
                            errors.append(Error(f, 'Missing acquisition date'))
                        break

    return (subject_ids, errors)


def check_zip_content(path, psc1=None, date=None, expected=None):
    """Rapid sanity check of a ZIP file containing imaging data for a subject.

    Expected sequences and tests are described as a dict:

    {
        'T1w': 'Good',
        'rest': 'Good',
        'B0_map': 'Good',
        'dwi': 'Doubtful',
        'dwi_rev': 'Bad',
        'FLAIR': 'Missing',
        'T2w', 'Good',
    }

    Parameters
    ----------
    path : str
        Path to the ZIP file.
    psc1 : str, optional
        Expected 12-digit PSC1 code.
    date : datetime.date, optional
        Date of acquisition.
    expected : dict, optional
        Which MRI sequences and tests to expect.

    Returns
    -------
    result: tuple
        In case of errors, return the tuple (psc1, errors) where psc1 is
        a collection of PSC1 codes found in the ZIP file and errors is an
        empty list if the ZIP file passes the check and a list of errors
        otherwise.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.

    """
    subject_ids = []
    errors = []

    basename = os.path.basename(path)

    # is the file empty?
    if os.path.getsize(path) == 0:
        errors.append(Error(basename, 'File is empty'))
        return (subject_ids, errors)

    # read the ZIP file into a tree structure
    try:
        ziptree = ZipTree.create(path)
    except BadZipFile as e:
        errors.append(Error(basename, 'Cannot unzip: "{0}"'.format(e)))
        return (subject_ids, errors)

    # check tree structure
    for f, z in ziptree.files.items():
        errors.append(Error(f, 'Unexpected file at the root of the ZIP file: {0}'
                               .format(f)))

    if expected:
        for sequence, status in expected.items():
            if status != 'Missing' and sequence not in ziptree.directories:
                errors.append(Error(basename,
                                    'Missing folder at the root of the ZIP file: {0}'
                                    .format(sequence)))
        for d, z in ziptree.directories.items():
            if d not in expected:
                errors.append(Error(basename,
                                    'Unexpected folder, unrelated to expected sequences: {0}'
                                    .format(d)))
            elif expected[d] == 'Missing':
                errors.append(Error(basename,
                                    'Unexpected folder, associated to a "Missing" sequence: {0}'
                                    .format(d)))
            else:
                s, e = _check_sequence_content(path, z, d, psc1, date)
                subject_ids.extend(s)
                errors.extend(e)
            errors.extend(_check_empty_files(z))

    return (subject_ids, errors)
