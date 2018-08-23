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
from datetime import datetime
from openpyxl import load_workbook
from .psytools import read_psytools

import logging
logger = logging.getLogger(__name__)
import sys
if (2, 7) <= sys.version_info < (3, 2):
    logger.addHandler(logging.NullHandler())

#
# reference files
#
_PSC_PATH = '/cveda/databank/framework/psc/psc2psc_2018-06-23.txt'
_RECRUITMENT_FILES_DIR = '/cveda/databank/framework/meta_data/recruitment_files'
_RECRUITMENT_FILES = (
    'recruitment_file_PGIMER.xlsx',
    'recruitment_file_IMPHAL.xlsx',
    'recruitment_file_KOLKATA.xlsx',
    'recruitment_file_RISHIVALLEY.xlsx',
    'recruitment_file_MYSORE.xlsx',
    'recruitment_file_NIMHANS.xlsx',
    'recruitment_file_SJRI.xlsx',
)
_ACE_IQ_PATH = '/cveda/databank/RAW/PSC1/psytools/cVEDA-cVEDA_ACEIQ-BASIC_DIGEST.csv'
_PHIR_PATH = '/cveda/databank/RAW/PSC1/psytools/cVEDA-cVEDA_PHIR-BASIC_DIGEST.csv'
_PDS_PATH = '/cveda/databank/RAW/PSC1/psytools/cVEDA-cVEDA_PDS-BASIC_DIGEST.csv'
_SDIM_PATH = '/cveda/databank/RAW/PSC1/psytools/cVEDA-cVEDA_SDIM-BASIC_DIGEST.csv'


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


def _read_excel(path):
    excel = {}
    workbook = load_workbook(path)
    for worksheet in workbook.worksheets:
        rows = list(worksheet.rows)
        index = {cell.value: i for i, cell in enumerate(rows[0])
                 if cell.value}
        if 'PSC1' not in index:
            logging.fatal('%s: PSC1 missing from header: %s',
                          path, index)
        for row in rows[1:]:
            psc1 = row[index['PSC1']].value
            if psc1:
                # clean up and detect invalid PSC1 codes
                if isinstance(psc1, int):
                    psc1 = str(psc1)
                psc1 = psc1.strip()
                if psc1.isdigit():
                    if len(psc1) != 12:
                        logger.error('invalid PSC1: %s', psc1)
                        psc1 = None
                else:
                    logger.warn('invalid PSC1: %s', psc1)
                    psc1 = None
            dob = row[index['DOB']].value
            if dob:
                # clean up and detect invalid dates of birth
                if isinstance(dob, str):
                    dob = dob.strip()
                    try:
                        dob = datetime.strptime(dob, '%d-%m-%Y').date()
                    except ValueError:
                        logger.error('invalid date of birth: %s', dob)
                        dob = None
                elif isinstance(dob, datetime):
                    dob = dob.date()
                else:
                    logger.error('invalid date of birth: %s', str(dob))
                    dob = None
            if psc1 and dob:
                excel[psc1] = dob
    return excel


def _initialize_dob_from_psc1(excel_paths, ace_iq_path, phir_path):
    """Build dictionnary to map PSC1 code to date of birth of subject.

    Parameters
    ----------
    excel_path : str
        Path to Excel file with authoritative dates of birth.
    ace_iq_path : str
        Path to ACE-IQ CSV file exported from Psytools.
    phir_path : str
        Path to PHIR CSV file exported from Psytools.

    Returns
    -------
    dict
        Maps PSC1 code to date of birth of subject.

    """
    dob_from_psc1 = {}

    excel = {}
    for excel_path in excel_paths:
        excel.update(_read_excel(excel_path))
    ace_iq_questions = {'ACEIQ_C2': 'datetime.date'}
    ace_iq = read_psytools(ace_iq_path, ace_iq_questions)
    phir_questions = {'PHIR_01': 'datetime.date'}
    phir = read_psytools(phir_path, phir_questions)
    for psc1 in set(excel) | set(ace_iq) | set(phir):
        if psc1 in excel:
            dob_excel = excel[psc1]
        else:
            dob_excel = None
        if psc1 in ace_iq and 'ACEIQ_C2' in ace_iq[psc1]:
            dob_ace_iq = ace_iq[psc1]['ACEIQ_C2']
        else:
            dob_ace_iq = None
        if psc1 in phir and 'PHIR_01' in phir[psc1]:
            dob_phir = phir[psc1]['PHIR_01']
        else:
            dob_phir = None
        if dob_excel:
            dob_from_psc1[psc1] = dob_excel
            if dob_ace_iq and dob_ace_iq != dob_excel:
                logger.info('ACE-IQ date of birth %s different from reference %s: %s',
                            dob_ace_iq, dob_excel, psc1)
            if dob_phir and dob_phir != dob_excel:
                logger.info('PHIR date of birth %s different from reference %s: %s',
                            dob_phir, dob_excel, psc1)
        elif dob_ace_iq and dob_phir:
            if dob_ace_iq == dob_phir:
                dob_from_psc1[psc1] = dob_ace_iq
            else:
                logger.error('inconsistent dates in ACE-IQ (%s) and PHIR (%s): %s',
                             dob_ace_iq, dob_phir, psc1)
        elif dob_ace_iq:
            logger.warn('missing PHIR and reference date of birth for: %s', psc1)
            dob_from_psc1[psc1] = dob_ace_iq
        elif dob_phir:
            logger.warn('missing ACE-IQ and reference date of birth for: %s', psc1)
            dob_from_psc1[psc1] = dob_phir
        else:  # huh? shouldn't be here if PSC1 found in a source at least
            logger.error('missing any date of birth for: %s', psc1)

    return dob_from_psc1


def _initialize_sex_from_psc1(ace_iq_path, pds_path, sdim_path):
    """Build dictionnary to map PSC1 code to sex of subject.

    Parameters
    ----------
    ace_iq_path : str
        Path to ACE-IQ CSV file exported from Psytools.
    pds_path : str
        Path to PDS CSV file exported from Psytools.
    sdim_path : str
        Path to SDIM CSV file exported from Psytools.

    Returns
    -------
    dict
        Maps PSC1 code to sex of subject.

    """
    sex_from_psc1 = {}

    ace_iq_questions = {'ACEIQ_C1': None}
    ace_iq = read_psytools(ace_iq_path, ace_iq_questions)
    pds_questions = {'PDS_gender': None}
    pds = read_psytools(pds_path, pds_questions)
    sdim_questions = {'SDI_02': None}
    sdim = read_psytools(sdim_path, sdim_questions)
    for psc1 in list(ace_iq) + list(pds) + list(sdim):
        merge = {}
        if psc1 in ace_iq and 'ACEIQ_C1' in ace_iq[psc1]:
            ace_iq_sex = ace_iq[psc1]['ACEIQ_C1']
            merge[ace_iq_sex] = merge.setdefault(ace_iq_sex, 0) + 1
        if psc1 in pds and 'PDS_gender' in pds[psc1]:
            pds_sex = pds[psc1]['PDS_gender']
            merge[pds_sex] = merge.setdefault(pds_sex, 0) + 1
        if psc1 in sdim and 'SDI_02' in sdim[psc1]:
            sdim_sex = sdim[psc1]['SDI_02']
            merge[sdim_sex] = merge.setdefault(sdim_sex, 0) + 1
        if len(merge) < 1:
            logger.warning('missing sex for: %s', psc1)
        elif len(merge) > 1:
            logger.info('inconsistent sex for: %s', psc1)
            # find the value that occurred more than any other
            reverse = {}
            for k, v in merge.items():
                reverse.setdefault(v, []).append(k)
            m = max(reverse.keys())
            if len(reverse[m]) == 1:
                sex_from_psc1[psc1] = reverse[m][0]
        else:
            sex_from_psc1[psc1] = list(merge.keys())[0]

    return sex_from_psc1


PSC2_FROM_PSC1 = _initialize_psc2_from_psc1(_PSC_PATH)
PSC1_FROM_PSC2 = {v: k for k, v in PSC2_FROM_PSC1.items()}
_recruitment_files = (os.path.join(_RECRUITMENT_FILES_DIR, recruitment_file)
                      for recruitment_file in _RECRUITMENT_FILES)
DOB_FROM_PSC1 = _initialize_dob_from_psc1(_recruitment_files, _ACE_IQ_PATH, _PHIR_PATH)
SEX_FROM_PSC1 = _initialize_sex_from_psc1(_ACE_IQ_PATH, _PDS_PATH, _SDIM_PATH)


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
