#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2010-2016 CEA
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

"""Re-encode and anonymize Psytools files.

This script iterates over Psytools CSV files downloaded from the Delosis
server. For each file it will:
* substitute the PSC1 code for a PSC2 code,
* change acquisition dates into age in days at acquisition,
* remove some data (such as date of birth) used for cross-checking.

==========
Attributes
==========

Input
-----

PSYTOOLS_PSC1_DIR : str
    Source directory to read PSC1-encoded Psytools files from.

Output
------

PSYTOOLS_PSC2_DIR : str
    Target directory to write PSC2-encoded Psytools files to.

"""

PSYTOOLS_PSC1_DIR = '/cveda/databank/BL/RAW/PSC1/psytools'
PSYTOOLS_PSC2_DIR = '/cveda/databank/BL/RAW/PSC2/psytools'

import logging
logging.basicConfig(level=logging.INFO)

import os
from datetime import time
from datetime import datetime

# import ../cveda_databank
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
from cveda_databank import PSC2_FROM_PSC1
from cveda_databank import DOB_FROM_PSC2


def _create_psc2_file(psc1_path, psc2_path):
    """Anonymize and re-encode a Psytools questionnaire from PSC1 to PSC2.

    Parameters
    ----------
    psc1_path: str
        Input: PSC1-encoded Psytools file.
    psc2_path: str
        Output: PSC2-encoded Psytools file.

    """
    with open(psc1_path, 'r') as psc1_file:
        # identify columns to anonymize in header
        header = psc1_file.readline().strip()
        convert = [i for i, field in enumerate(header.split(','))
                   if 'Timestamp' in field]
        with open(psc2_path, 'w') as psc2_file:
            psc2_file.write(header + '\n')
            for line in psytools_file:
                line = line.strip()
                items = line.split(',')
                psc1 = items[0]
                if 'id_check' in line:
                    # Psytools files contain identifying data,
                    # specifically lines containing items:
                    # * id_check_dob
                    # * id_check_gender
                    #
                    # As the name implies, the purpose of these items is
                    # cross-checking and error detection. They should not
                    # be used for scientific purposes.
                    #
                    # These items should therefore not be exposed to end
                    # users.
                    logging.debug('skipping line with "id_check" from {0}'
                                  .format(psc1))
                    continue
                # subject ID is PSC1 followed by '-C' or '-I'
                if '-' in psc1:
                    psc1, suffix = psc1.rsplit('-', 1)
                else:
                    suffix = None
                psc2 = None
                if psc1.startswith('TEST'):
                    logging.debug('skipping test subject {0}'
                                  .format(psc1))
                    continue
                elif psc1 in PSC2_FROM_PSC1:
                    logging.debug('converting subject {0} from PSC1 to PSC2'
                                  .format(psc1))
                    psc2 = PSC2_FROM_PSC1[psc1]
                    items[0] = '-'.join((psc2, suffix))
                else:
                    logging.error('PSC1 code missing from conversion table: {0}'
                                  .format(items[0]))
                    continue
                for i in convert:
                    if psc2 is None or psc2 not in DOB_FROM_PSC2:
                        items[i] = ''
                    else:
                        timestamp = datetime.strptime(items[i],
                                                      '%Y-%m-%d %H:%M:%S.%f').date()
                        birth = DOB_FROM_PSC2[psc2]
                        age = timestamp - birth
                        items[i] = str(age.days)
                psc2_file.write(','.join(items) + '\n')


def create_psc2_files(psc1_dir, psc2_dir):
    """Anonymize and re-encode all psytools questionnaires within a directory.

    PSC1-encoded files are read from `master_dir`, anoymized and converted
    from PSC1 codes to PSC2, and the result is written in `psc2_dir`.

    Parameters
    ----------
    psc1_dir: str
        Input directory with PSC1-encoded questionnaires.
    psc2_dir: str
        Output directory with PSC2-encoded and anonymized questionnaires.

    """
    for psc1_file in os.listdir(psc1_dir):
        psc1_path = os.path.join(psc1_dir, psc1_file)
        psc2_path = os.path.join(psc2_dir, psc1_file)
        _create_psc2_file(psc1_path, psc2_path)


def main():
    create_psc2_files(PSYTOOLS_PSC1_DIR, PSYTOOLS_PSC2_DIR)


if __name__ == "__main__":
    main()
