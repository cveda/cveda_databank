#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2017 CEA
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

"""Check date of birth (DOB) and/or age can be found in ACE-IQ and PHIR
questionnaires and are consistent.

==========
Attributes
==========

Input
------

ACEIQ : str
    ACE-IQ questionnaire as exported from the Delosis server as a CSV file.

PHIR : str
    PHIR questionnaire as exported from the Delosis server as a CSV file.

EXCEL : str
    Excel file supposed to contain the correct date of birth

"""

from csv import (Sniffer, DictReader)
from datetime import datetime
from openpyxl import load_workbook

import logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger()


ACE_IQ = '/cveda/databank/BL/RAW/PSC1/psytools/cVEDA-cVEDA_ACEIQ-BASIC_DIGEST.csv'
PHIR = '/cveda/databank/BL/RAW/PSC1/psytools/cVEDA-cVEDA_PHIR-BASIC_DIGEST.csv'
EXCEL = '/tmp/PSC1_DOB_2017-01-21.xlsx'


def age(today, birth):
    # http://stackoverflow.com/a/9754466/65387
    return (today.year - birth.year -
            ((today.month, today.day) < (birth.month, birth.day)))


def read_ace_iq(path):
    ace_iq = {}
    with open(path, mode='r', newline='') as csvfile:
        dialect = Sniffer().sniff(csvfile.read(4096))
        csvfile.seek(0)
        reader = DictReader(csvfile, dialect=dialect)
        for row in reader:
            trial = row['Trial']
            if trial in {'ACEIQ_C2', 'ACEIQ_C3'}:
                psc1 = row['User code']
                if psc1[-3:-1] == '-C':  # user code ID of the form <PSC1>-C1, <PSC1>-C3, etc.
                    psc1 = psc1[:-3]
                if len(psc1) != 12 or not psc1.isdigit():
                    logger.warn('bogus PSC1: %s', psc1)
                    continue
                result = row['Trial result']
                if result != 'skip_back':
                    psc1_value = ace_iq.setdefault(psc1, {})
                    iteration = int(row['Iteration'])
                    iteration_value = psc1_value.setdefault(iteration, {})
                    result = row['Trial result']
                    if result != '':
                        if trial == 'ACEIQ_C2':
                            dob = datetime.strptime(result, '%d-%m-%Y')
                            iteration_value['dob'] = dob.date()  # overwrite previous results
                            completed = datetime.strptime(row['Completed Timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                            iteration_value['age_from_dob'] = age(completed, dob)
                        elif trial == 'ACEIQ_C3':
                            iteration_value['age'] = int(result)  # overwrite previous results
    for psc1, value in ace_iq.items():
        ace_iq[psc1] = value[max(value.keys())]  # keep last iteration only
    return ace_iq


def read_phir(path):
    phir = {}
    with open(path, mode='r', newline='') as csvfile:
        dialect = Sniffer().sniff(csvfile.read(4096))
        csvfile.seek(0)
        reader = DictReader(csvfile, dialect=dialect)
        for row in reader:
            trial = row['Trial']
            if trial in {'PHIR_01'}:
                psc1 = row['User code']
                if psc1[-3:-1] == '-C':  # user code ID of the form <PSC1>-C1, <PSC1>-C3, etc.
                    psc1 = psc1[:-3]
                if len(psc1) != 12 or not psc1.isdigit():
                    logger.warn('bogus PSC1: %s', psc1)
                    continue
                result = row['Trial result']
                if result != 'skip_back':
                    psc1_value = phir.setdefault(psc1, {})
                    iteration = int(row['Iteration'])
                    iteration_value = psc1_value.setdefault(iteration, {})
                    if result != '':
                        if trial == 'PHIR_01':
                            dob = datetime.strptime(result, '%d-%m-%Y')
                            iteration_value['dob'] = dob.date()
                            completed = datetime.strptime(row['Completed Timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                            iteration_value['age_from_dob'] = age(completed, dob)
    for psc1, value in phir.items():
        phir[psc1] = value[max(value.keys())]  # keep last iteration only
    return phir


def read_excel(path):
    excel = {}
    workbook = load_workbook(path)
    for worksheet in workbook:
        for row in worksheet:
            psc1 = row[0].value
            dob = row[1].value
            if not psc1:
                continue
            if isinstance(psc1, int):
                psc1 = str(psc1)
            psc1 = psc1.strip()
            if psc1.isdigit():
                if len(psc1) != 12:
                    logger.error('bogus PSC1: %s', psc1)
                    continue
            else:
                logger.warn('bogus PSC1: %s', psc1)
                continue
            if not dob:
                continue
            if isinstance(dob, str):
                if dob.startswith('…'):  # blank cells...
                    continue
                dob = dob.strip()
                try:
                    dob = datetime.strptime(dob, '%d/%m/%Y').date()
                except ValueError:
                    try:
                        dob = datetime.strptime(dob, '%d.%m.%Y').date()
                    except ValueError:
                        try:
                            dob = datetime.strptime(dob, '%d/%m%Y').date()  # ouch! single occurrence
                        except ValueError:
                            logger.error('bogus DOB: %s', dob)
            elif isinstance(dob, datetime):
                dob = dob.date()
            else:
                logger.error('bogus DOB: %s', str(dob))
            excel[psc1] = dob
    return excel


def main():
    # ACE-IQ questionnaire
    ace_iq = read_ace_iq(ACE_IQ)

    # PHIR questionnaire
    phir = read_phir(PHIR)

    # Excel additional file
    excel = read_excel(EXCEL)

    for psc1 in set(ace_iq) & set(phir) & set(excel):
        dob_ace_iq = None
        if psc1 in ace_iq and 'dob' in ace_iq[psc1]:
            dob_ace_iq = ace_iq[psc1]['dob']
        dob_phir = None
        if psc1 in phir and 'dob' in phir[psc1]:
            dob_phir = phir[psc1]['dob']
        dob_excel = None
        if psc1 in excel:
            dob_excel = excel[psc1]

        if dob_ace_iq and dob_phir:
            if dob_ace_iq != dob_phir:
                if dob_excel:
                    if dob_excel == dob_ace_iq:
                        print('{}: PHIR date of birth is different from ACE-IQ and Excel dates of birth: {} / {}'
                              .format(psc1, dob_excel, dob_phir))
                    elif dob_excel == dob_phir:
                        print('{}: ACE-IQ date of birth is different from PHIR and Excel dates of birth: {} / {}'
                              .format(psc1, dob_excel, dob_ace_iq))
                    else:
                        print('{}: All dates of birth are different: {} / {} / {}'
                              .format(psc1, dob_excel, dob_ace_iq, dob_phir))
                else:
                    print('{}: Missing Excel date of birth, different ACE-IQ and PHIR dates of birth: {} / {}'
                          .format(psc1, dob_ace_iq, dob_phir))
        elif dob_ace_iq:
            if dob_excel:
                if dob_excel != dob_ace_iq:
                    print('{}: ACE-IQ date of birth is different from Excel date of birth: {} / {}'
                          .format(psc1, dob_excel, dob_ace_iq))
            else:
                print('{}: Missing Excel date of birth, only ACE-IQ date of birth: {} / {}'
                      .format(psc1, dob_ace_iq))
        elif dob_phir:
            if dob_excel:
                if dob_excel != dob_phir:
                    print('{}: PHIR date of birth is different from Excel date of birth: {} / {}'
                          .format(psc1, dob_excel, dob_phir))
            else:
                print('{}: Missing Excel date of birth, only PHIR date of birth: {} / {}'
                      .format(psc1, dob_phir))
        elif dob_excel:
            print('{}: Orphan Excel entry'
                  .format(psc1))
        else:
            print('{}: Uh???'
                  .format(psc1))


if __name__ == "__main__":
    main()
