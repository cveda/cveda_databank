# -*- coding: utf-8 -*-

# Copyright (c) 2014-2018 CEA
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
import pandas
from datetime import datetime

import logging
logger = logging.getLogger(__name__)
import sys
if (2, 7) <= sys.version_info < (3, 2):
    logger.addHandler(logging.NullHandler())

if sys.version_info[0] < 3:
    integer_types = (int, long)
else:
    integer_types = (int,)

# PSC1 to PSC2 conversion table
_PSC_PATH = '/cveda/databank/framework/psc/psc2psc_2019-02-07.txt'

# recruitment file with reference date of birth / sex information
_RECRUITMENT_FILES_DIR = '/cveda/databank/framework/meta_data/recruitment'
_RECRUITMENT_FILES = (
    'recruitment_file_PGIMER_2019-06-12.xlsx',
    'recruitment_file_IMPHAL_2019-06-06.xlsx',
    'recruitment_file_KOLKATA_2019-06-06.xlsx',
    'recruitment_file_RISHIVALLEY_2019-06-06.xlsx',
    'recruitment_file_MYSORE_2019-06-06.xlsx',
    'recruitment_file_NIMHANS_2019-06-06.xlsx',
    'recruitment_file_SJRI_2019-09-12.xlsx',
)


def _initialize_psc2_from_psc1(path):
    """Returns dictionnary to map PSC1 to PSC2.

    Parameters
    ----------
    path : str

    Returns
    -------
    dict
        Maps PSC1 code to PSC2.

    """
    psc2_from_psc1 = {}
    with open(_PSC_PATH, 'rU') as f:
        for line in f:
            psc1, psc2 = line.strip().split(',')
            if psc2 in psc2_from_psc1:
                if psc2_from_psc1[psc1] != psc2:
                    logger.critical('inconsistent PSC1/PSC2 mapping: %s', path)
                    raise Exception('inconsistent PSC1/PSC2 mapping')
                else:
                    logger.warning('duplicate PSC1/PSC2 mapping: %s', path)
            else:
                psc2_from_psc1[psc1] = psc2
    return psc2_from_psc1


def _read_recruitment_file(path):
    with pandas.ExcelFile(path) as excel_file:
        converters = {
            'PSC1': str,
        }
        return pandas.read_excel(path, converters=converters)


def _read_recruitment_files(paths):
    return pandas.concat((_read_recruitment_file(path) for path in paths),
                         ignore_index=True)


def _initialize_dob_sex(paths):
    """Build dictionnary to map PSC1 code to date of birth of subject.

    Parameters
    ----------
    recruitment_data : pandas.DataFrame
        Data read from recruitment files.

    Returns
    -------
    dict
        Maps PSC1 code to date of birth of subject.

    """
    recruitment_data = _read_recruitment_files(paths)

    dob_from_psc1 = {}
    sex_from_psc1 = {}
    for row in recruitment_data.itertuples(index=False):
        psc1 = row.PSC1

        if pandas.isnull(row.DOB):
            logger.error('%s: invalid value for date of birth: %s', psc1, row.DOB)
        else:
            dob = row.DOB.date()
            if psc1 not in dob_from_psc1:
                dob_from_psc1[psc1] = dob
            elif dob == dob_from_psc1[psc1]:
                logger.warning('%s: duplicate PSC1 code in recruitment file', psc1)
            else:
                logger.error('%s: inconsistent duplicate PSC1 code in recruitment file', psc1)

        if row.SEX not in {'F', 'M'}:
            logger.error('%s: invalid value for sex: "%s"', psc1, row.SEX)
        elif psc1 not in sex_from_psc1:
            sex_from_psc1[psc1] = row.SEX
        elif row.SEX == sex_from_psc1[psc1]:
            logger.warning('%s: duplicate PSC1 code in recruitment file', psc1)
        else:
            logger.error('%s: inconsistent duplicate PSC1 code in recruitment file', psc1)

    return dob_from_psc1, sex_from_psc1


PSC2_FROM_PSC1 = _initialize_psc2_from_psc1(_PSC_PATH)
PSC1_FROM_PSC2 = {v: k for k, v in PSC2_FROM_PSC1.items()}
DOB_FROM_PSC1, SEX_FROM_PSC1 = _initialize_dob_sex(os.path.join(_RECRUITMENT_FILES_DIR, f)
                                                   for f in _RECRUITMENT_FILES)


def age_band(age):
    """Theoretical age band from age.

    Parameters
    ----------
    age : int
        Age in years.

    Returns
    -------
    str
        One of 'C1', 'C2', 'C3'.

    """
    if age <= 11:
        age_band = 'C1'  # 6-11
    elif age <= 17:
        age_band = 'C2'  # 12-17
    else:
        age_band = 'C3'  # 18-23
    return age_band


class Error:
    """The `Error` exception is raised when an error occurs while parsing
    c-VEDA data files.

    Attributes
    ----------
    path : str
        Path to the file containing erroneous data.
    message : str
        Message explaining the error.
    sample : str
        Data extracted from the file that caused the error.

    """
    _SAMPLE_LEN = 30

    def __init__(self, path, message, sample=None):
        self.path = path
        self.message = message
        self.sample = sample

    def __str__(self):
        if self.path:
            if self.sample:
                sample = repr(self.sample)
                if len(sample) > self._SAMPLE_LEN:
                    sample = sample[:self._SAMPLE_LEN] + '...'
                return '{0}: <{1}>: {2}'.format(self.message, sample, self.path)
            else:
                return '{0}: {1}'.format(self.message, self.path)
        else:
            return '{0}'.format(self.message)
