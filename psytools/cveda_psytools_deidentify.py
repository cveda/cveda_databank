#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2010-2018 CEA
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

PSYTOOLS_PSC1_DIR = '/cveda/databank/RAW/PSC1/psytools'
PSYTOOLS_PSC2_DIR = '/cveda/databank/RAW/PSC2/psytools'

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

        # de-identify columns that contain dates
        ANONYMIZED_COLUMNS = {
            'Completed Timestamp': '%Y-%m-%d %H:%M:%S.%f',
            'Processed Timestamp': '%Y-%m-%d %H:%M:%S.%f',
        }
        convert = [fieldname for fieldname in psc1_reader.fieldnames
                   if fieldname in ANONYMIZED_COLUMNS]

        with open(psc2_path, 'w') as psc2_file:
            psc2_writer = DictWriter(psc2_file, psc1_reader.fieldnames, dialect='excel')
            psc2_writer.writeheader()
            for row in psc1_reader:
                trial = row['Trial']
                # Psytools files contain identifying data,
                # specifically lines containing items:
                # - ID_check_dob
                # - ID_check_gender
                #
                # As the name implies, the purpose of these items is
                # cross-checking and error detection. They should not
                # be used for scientific purposes.
                #
                # These items should therefore not be exposed to Imagen
                # users.
                #
                # The Scito anoymization pipeline used not to filter
                # these items out. Since the Imagen V2 server exposes raw
                # Psytools files to end users, we need to remove these
                # items sooner, before importing the data into the
                # CubicWeb database.
                if 'ID_check_' in trial:
                    logging.debug('skipping line with "ID_check_" for %s',
                                  row['User code'])
                    continue

                # subject ID is PSC1 followed by either of:
                #   -C1  age band 6-11
                #   -C2  age band 12-17
                #   -C3  age band 18-23
                psc1_suffix = row['User code'].rsplit('-', 1)
                psc1 = psc1_suffix[0]
                if psc1.endswith('FU1'):
                    psc1 = psc1[:-len('FU1')]
                    fu = psc1[-len('FU1'):]
                elif psc1.endswith('FU2'):
                    psc1 = psc1[:-len('FU2')]
                    fu = psc1[-len('FU2'):]
                elif psc1.endswith('FUMRI1'):
                    psc1 = psc1[:-len('FUMRI1')]
                    fu = 'FU1'
                elif psc1.endswith('FUMRI2'):
                    psc1 = psc1[:-len('FUMRI2')]
                    fu = 'FU2'
                else:
                    fu = None
                if psc1 in PSC2_FROM_PSC1:
                    psc2 = PSC2_FROM_PSC1[psc1]
                    if fu:
                        psc2 += fu
                    if len(psc1_suffix) > 1:
                        psc2_suffix = '-'.join((psc2, psc1_suffix[1]))
                    else:
                        psc2_suffix = psc2
                    logging.debug('converting from %s to %s',
                                  row['User code'], psc2_suffix)
                    row['User code'] = psc2_suffix
                else:
                    u = psc1.upper()
                    if ('DEMO' in u or 'MOCK' in u or 'NPPILOT' in u
                            or 'TEST' in u):
                        logging.debug('skipping test subject %s',
                                      row['User code'])
                    else:
                        logging.error('unknown PSC1 code %s in user code %s',
                                      psc1, row['User code'])
                    continue

                # de-identify columns that contain dates
                for fieldname in convert:
                    if psc1 in DOB_FROM_PSC1:
                        birth = DOB_FROM_PSC1[psc1]
                        timestamp = datetime.strptime(row[fieldname],
                                                      ANONYMIZED_COLUMNS[fieldname]).date()
                        age = timestamp - birth
                        row[fieldname] = str(age.days)
                    else:
                        row[fieldname] = None

                # de-identify rows that contain dates
                #
                # ACEIQ_C2: What is your date of birth?
                # PHIR_01: What is (child's name) birthdate?
                if trial == 'ACEIQ_C2' or trial == 'PHIR_01':
                    if psc1 in DOB_FROM_PSC1:
                        birth = DOB_FROM_PSC1[psc1]
                        try:
                            d = datetime.strptime(row['Trial result'],
                                                  '%d-%m-%Y').date()
                        except ValueError:
                            row['Trial result'] = None
                        else:
                            age = d - birth
                            row['Trial result'] = str(age.days)
                    else:
                        row['Trial result'] = None
                # PDS_07a: What was the date of your first period?
                elif trial == 'PDS_07a':
                    if psc1 in DOB_FROM_PSC1:
                        birth = DOB_FROM_PSC1[psc1]
                        try:
                            d = datetime.strptime(row['Trial result'],
                                                  '%m-%Y').date()
                        except ValueError:
                            row['Trial result'] = None
                        else:
                            age = d - birth
                            row['Trial result'] = str(age.days)
                    else:
                        row['Trial result'] = None
                # PHIR_02: What is your birthdate?
                elif trial == 'PHIR_02':
                    try:
                        birth = datetime.strptime(row['Trial result'],
                                                  '%d-%m-%Y').date()
                    except ValueError:
                        row['Trial result'] = None
                    else:
                        # last 'timestamp' ought to be 'Processed timestamp'
                        age = timestamp - birth
                        row['Trial result'] = str(age.days)

                psc2_writer.writerow(row)


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
