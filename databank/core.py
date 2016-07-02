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

import re
import datetime

import logging
logger = logging.getLogger(__name__)

#
# reference file that maps birth dates, PSC1 and PSC2 codes
#
_PSC_PATH = '/dev/null'  # '/cveda/psc.csv'
_DOB_PATH = '/dev/null'  # '/cveda/dob.csv'


def _initialize_psc2_from_psc1(path):
    """Returns dictionnary to map PSC1 to PSC2.

    Parameters
    ----------
    path : unicode

    Returns
    -------
    dict
        Dictionnary to map PSC1 code to PSC2.

    """
    psc2_from_psc1 = {}
    with open(_PSC_PATH, 'rU') as f:
        for line in f:
            psc1, psc2 = line.strip('\n').split(',').strip()
            if psc2 in psc2_from_psc1:
                if psc2_from_psc1[psc1] != psc2:
                    logger.critical('inconsistent PSC1/PSC2 mapping: %s', path)
                    raise Exception('inconsistent PSC1/PSC2 mapping')
                else:
                    logger.warning('duplicate PSC1/PSC2 mapping: %s', path)
            else:
                psc2_from_psc1[psc1] = psc2
    return psc2_from_psc1


_REGEX_DOB = re.compile(r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})')


def _initialize_dob_from_psc1(path):
    """Returns dictionnary to map PSC1 code to date of birth.

    Parameters
    ----------
    path : unicode

    Returns
    -------
    dict
        Dictionnary to map PSC1 code to date of birth.

    """
    dob_from_psc1 = {}
    with open(_DOB_PATH, 'rU') as f:
        for line in f:
            psc1, dob = line.strip('\n').split(',').strip()
            match = _REGEX_DOB.match(dob)
            if match:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                if year > 2016:  # c-VEDA started in 2016
                    logger.error('unexpected birth date: %s: %s', dob, path)
                    raise Exception('unexpected birth date: {0}'.format(dob))
                dob_from_psc1[psc1] = datetime.date(year, month, day)
            else:
                logger.error('unexpected line: %s: %s', path, line)
                raise Exception('unexpected line: {0}'.format(line))
    return dob_from_psc1


PSC2_FROM_PSC1 = _initialize_psc2_from_psc1(_PSC_PATH)
PSC1_FROM_PSC2 = {v: k for k, v in PSC2_FROM_PSC1.items()}
DOB_FROM_PSC1 = _initialize_dob_from_psc1(_DOB_PATH)


class Error:
    """Error while parsing files.

    Returned by functions that parse imaging data.

    Attributes
    ----------
    path : str
        File name.
    message : str
        Message explaining the error.

    """

    def __init__(self, path, message):
        self.path = path
        self.message = message

    def __str__(self):
        if self.path:
            return '{0}: {1}'.format(self.message, self.path)
        else:
            return '{0}'.format(self.message)
