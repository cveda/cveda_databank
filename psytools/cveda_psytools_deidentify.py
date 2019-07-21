#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2010-2019 CEA
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

This script iterates over derived Psytools CSV files. For each file it will:
* substitute the PSC1 code for a PSC2 code,
* change event dates into age in days at event.

==========
Attributes
==========

Input
-----

PSYTOOLS_DERIVED_DIR : str
    Source directory to read derived PSC1-encoded Psytools files from.

Output
------

PSYTOOLS_PSC2_DIR : str
    Target directory to write PSC2-encoded Psytools files into.

"""

PSYTOOLS_DERIVED_DIR = '/cveda/chroot/data/tmp/psytools'
PSYTOOLS_PSC2_DIR = '/cveda/databank/processed/psytools'

import logging
logging.basicConfig(level=logging.ERROR)

import os
from csv import DictReader
from csv import DictWriter
from datetime import datetime

# import ../cveda_databank
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
from cveda_databank import PSC2_FROM_PSC1
from cveda_databank import DOB_FROM_PSC1


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
        psc1_reader = DictReader(psc1_file, dialect='excel')

        # de-identify columns with timestamps
        ANONYMIZED_COLUMNS = {
            'Completed Timestamp': '%Y-%m-%d %H:%M:%S.%f',
            'Processed Timestamp': '%Y-%m-%d %H:%M:%S.%f',
        }
        convert = [fieldname for fieldname in psc1_reader.fieldnames
                   if fieldname in ANONYMIZED_COLUMNS]

        # discard other columns with dates
        DISCARDED_COLUMNS = {
            'ID_check_dob', 'ID_check_gender',
        }

        # read/process each row and save for later writing
        rows = {}
        for row in psc1_reader:
            psc1 = row['User code']
            if psc1 in PSC2_FROM_PSC1:
                psc2 = PSC2_FROM_PSC1[psc1]
                logging.debug('converting from %s to %s',
                              row['User code'], psc2)
                row['User code'] = psc2
            else:
                logging.error('unknown PSC1 code %s in user code %s',
                              psc1, row['User code'])
                continue

            # de-identify columns with timestamps
            for fieldname in convert:
                if psc1 in DOB_FROM_PSC1:
                    birth = DOB_FROM_PSC1[psc1]
                    try:
                        timestamp = datetime.strptime(row[fieldname],
                                                      ANONYMIZED_COLUMNS[fieldname]).date()
                    except ValueError:
                        logging.error('%s: invalid "%s": %s',
                                      psc1, fieldname, row[fieldname])
                        row[fieldname] = None
                    else:
                        age = timestamp - birth
                        row[fieldname] = str(age.days)
                else:
                    row[fieldname] = None

            # convert to age in days at date of birth - should be 0 if correct!
            # ACEIQ_C2: What is your date of birth?
            # PHIR_01: What is (child's name) birthdate?
            for column in ('ACEIQ_C2', 'PHIR_01'):
                if column in psc1_reader.fieldnames:
                    if psc1 in DOB_FROM_PSC1:
                        birth = DOB_FROM_PSC1[psc1]
                        try:
                            d = datetime.strptime(row[column],
                                                  '%d-%m-%Y').date()
                        except ValueError:
                            row[column] = None
                        else:
                            age = d - birth
                            row[column] = str(age.days)
                    else:
                        row[column] = None

            # convert to age in days at the date of first period
            # PDS_07a: What was the date of your first period?
            column = 'PDS_07a'
            if column in psc1_reader.fieldnames:
                if psc1 in DOB_FROM_PSC1:
                    birth = DOB_FROM_PSC1[psc1]
                    try:
                        d = datetime.strptime(row[column],
                                              '%m-%Y').date()
                    except ValueError:
                        row[column] = None
                    else:
                        age = d - birth
                        row[column] = str(age.days)
                else:
                    row[column] = None

            # PHIR_02: What is your birthdate?
            column = 'PHIR_02'
            if column in psc1_reader.fieldnames:
                try:
                    birth = datetime.strptime(row[column],
                                              '%d-%m-%Y').date()
                except ValueError:
                    row[column] = None
                else:
                    # last 'timestamp' ought to be 'Processed timestamp'
                    age = timestamp - birth
                    row[column] = str(age.days)

            # discard other columns with dates
            for column in DISCARDED_COLUMNS:
                if column in psc1_reader.fieldnames:
                    del row[column]

            rows.setdefault(psc2, []).append(row)

        # save rows into output file, sort by PSC2
        with open(psc2_path, 'w') as psc2_file:
            fieldnames = [fieldname for fieldname in psc1_reader.fieldnames
                          if fieldname not in DISCARDED_COLUMNS]
            psc2_writer = DictWriter(psc2_file, fieldnames, dialect='excel')
            psc2_writer.writeheader()
            for psc2 in sorted(rows):
                for row in rows[psc2]:
                    psc2_writer.writerow(row)


def create_psc2_files(psc1_dir, psc2_dir):
    """Anonymize and re-encode all psytools questionnaires within a directory.

    PSC1-encoded files are read from `psc1_dir`, anoymized and converted
    from PSC1 codes to PSC2, and the result is written in `psc2_dir`.

    Parameters
    ----------
    psc1_dir: str
        Input directory with PSC1-encoded derived questionnaires.
    psc2_dir: str
        Output directory with PSC2-encoded and anonymized questionnaires.

    """
    for psc1_file in os.listdir(psc1_dir):
        psc1_path = os.path.join(psc1_dir, psc1_file)
        psc2_path = os.path.join(psc2_dir, psc1_file)
        _create_psc2_file(psc1_path, psc2_path)


def main():
    create_psc2_files(PSYTOOLS_DERIVED_DIR, PSYTOOLS_PSC2_DIR)


if __name__ == "__main__":
    main()
