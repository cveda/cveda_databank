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

"""

import csv
import sys
import datetime
import xlsxwriter

ACE_IQ = '/cveda/databank/BL/RAW/PSC1/psytools/cVEDA-cVEDA_ACEIQ-BASIC_DIGEST.csv'
PHIR = '/cveda/databank/BL/RAW/PSC1/psytools/cVEDA-cVEDA_PHIR-BASIC_DIGEST.csv'


def age(today, birth):
    # http://stackoverflow.com/a/9754466/65387
    return (today.year - birth.year -
            ((today.month, today.day) < (birth.month, birth.day)))


def read_ace_iq(path):
    ace_iq = {}
    with open(path, mode='r', newline='') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(4096))
        csvfile.seek(0)
        reader = csv.DictReader(csvfile, dialect=dialect)
        for row in reader:
            trial = row['Trial']
            if trial in {'ACEIQ_C2', 'ACEIQ_C3'}:
                psc1 = row['User code']
                if psc1[-3:-1] == '-C':  # user code ID of the form <PSC1>-C1, <PSC1>-C3, etc.
                    psc1 = psc1[:-3]
                result = row['Trial result']
                if result != 'skip_back':
                    psc1_value = ace_iq.setdefault(psc1, {})
                    iteration = int(row['Iteration'])
                    iteration_value = psc1_value.setdefault(iteration, {})
                    result = row['Trial result']
                    if result != '':
                        if trial == 'ACEIQ_C2':
                            dob = datetime.datetime.strptime(result, '%d-%m-%Y')
                            iteration_value['dob'] = dob.date()  # overwrite previous results
                            completed = datetime.datetime.strptime(row['Completed Timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                            iteration_value['age_from_dob'] = age(completed, dob)
                        elif trial == 'ACEIQ_C3':
                            iteration_value['age'] = int(result)  # overwrite previous results
    for psc1, value in ace_iq.items():
        ace_iq[psc1] = value[max(value.keys())]  # keep last iteration only
    return ace_iq


def read_phir(path):
    phir = {}
    with open(path, mode='r', newline='') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(4096))
        csvfile.seek(0)
        reader = csv.DictReader(csvfile, dialect=dialect)
        for row in reader:
            trial = row['Trial']
            if trial in {'PHIR_01'}:
                psc1 = row['User code']
                if psc1[-3:-1] == '-C':  # user code ID of the form <PSC1>-C1, <PSC1>-C3, etc.
                    psc1 = psc1[:-3]
                result = row['Trial result']
                if result != 'skip_back':
                    psc1_value = phir.setdefault(psc1, {})
                    iteration = int(row['Iteration'])
                    iteration_value = psc1_value.setdefault(iteration, {})
                    if result != '':
                        if trial == 'PHIR_01':
                            dob = datetime.datetime.strptime(result, '%d-%m-%Y')
                            iteration_value['dob'] = dob.date()
                            completed = datetime.datetime.strptime(row['Completed Timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                            iteration_value['age_from_dob'] = age(completed, dob)
    for psc1, value in phir.items():
        phir[psc1] = value[max(value.keys())]  # keep last iteration only
    return phir


def main():
    # ACE-IQ questionnaire
    ace_iq = read_ace_iq(ACE_IQ)

    # PHIR questionnaire
    phir = read_phir(PHIR)

    # Excel output
    options = {
        'strings_to_numbers': False,
    }
    workbook = xlsxwriter.Workbook('cVEDA_Psytools.xlsx', options)
    HEADER_FORMAT = workbook.add_format({'bold': True,
                                         'align': 'center', 'valign': 'vcenter'})
    worksheet = workbook.add_worksheet('date of birth - age')
    # PSC1
    worksheet.merge_range(0, 0, 1, 0, u'PSC1', HEADER_FORMAT)
    worksheet.set_column(0, 0, 14)
    # ACE-IQ
    worksheet.merge_range(0, 1, 0, 3, u'ACE-IQ', HEADER_FORMAT)
    worksheet.write(1, 1, u'date of birth', HEADER_FORMAT)
    worksheet.write(1, 2, u'age', HEADER_FORMAT)
    worksheet.write(1, 3, u'computed age', HEADER_FORMAT)
    worksheet.set_column(1, 3, 16)
    # PHIR
    worksheet.merge_range(0, 4, 0, 5, u'PHIR', HEADER_FORMAT)
    worksheet.write(1, 4, u'date of birth', HEADER_FORMAT)
    worksheet.write(1, 5, u'computed age', HEADER_FORMAT)
    worksheet.set_column(4, 5, 16)
    # more formatting and prepare for writing data
    worksheet.freeze_panes(2, 0)
    error_format = {'bg_color': '#FF6A6A'}
    ERROR_FORMAT = workbook.add_format(error_format)
    date_format = {'num_format': 'yyyy-mm-dd'}
    DATE_FORMAT = workbook.add_format(date_format)
    date_format.update(error_format)
    DATE_ERROR_FORMAT = workbook.add_format(date_format)
    row = 2

    for psc1 in ace_iq.keys() & phir.keys():
        ace_iq_dob = None
        ace_iq_age = None
        ace_iq_age_from_dob = None
        phir_dob = None
        phir_age_from_dob = None
        if psc1 in ace_iq:
            if 'dob' in ace_iq[psc1]:
                ace_iq_dob = ace_iq[psc1]['dob']
            if 'age' in ace_iq[psc1]:
                ace_iq_age = ace_iq[psc1]['age']
            if 'age_from_dob' in ace_iq[psc1]:
                ace_iq_age_from_dob = ace_iq[psc1]['age_from_dob']
        if psc1 in phir:
            if 'dob' in phir[psc1]:
                phir_dob = phir[psc1]['dob']
            if 'age_from_dob' in phir[psc1]:
                phir_age_from_dob = phir[psc1]['age_from_dob']

        if psc1.startswith('1'):
            error = False
            # date of birth
            if ace_iq_dob and phir_dob and ace_iq_dob != phir_dob:
                error = True
                if ace_iq_age and (ace_iq_age == phir_age_from_dob and
                                   ace_iq_age != ace_iq_age_from_dob):
                    col_1 = (ace_iq_dob, DATE_ERROR_FORMAT)
                    col_4 = (phir_dob, DATE_FORMAT)
                elif ace_iq_age and (ace_iq_age == ace_iq_age_from_dob and
                                     ace_iq_age != phir_age_from_dob):
                    col_1 = (ace_iq_dob, DATE_FORMAT)
                    col_4 = (phir_dob, DATE_ERROR_FORMAT)
                else:
                    col_1 = (ace_iq_dob, DATE_ERROR_FORMAT)
                    col_4 = (phir_dob, DATE_ERROR_FORMAT)
            else:
                col_1 = (ace_iq_dob, DATE_FORMAT)
                col_4 = (phir_dob, DATE_FORMAT)
            # age
            col_2 = (ace_iq_age, None)
            if ace_iq_age:
                if ace_iq_age_from_dob and ace_iq_age != ace_iq_age_from_dob:
                    error = True
                    age_error = True
                    col_3 = (ace_iq_age_from_dob, ERROR_FORMAT)
                    col_2 = (ace_iq_age, ERROR_FORMAT)
                else:
                    col_3 = (ace_iq_age_from_dob, None)
                if phir_age_from_dob and ace_iq_age != phir_age_from_dob:
                    error = True
                    age_error = True
                    col_5 = (phir_age_from_dob, ERROR_FORMAT)
                    col_2 = (ace_iq_age, ERROR_FORMAT)
                else:
                    col_5 = (phir_age_from_dob, None)
            else:
                col_3 = (ace_iq_age_from_dob, None)
                col_5 = (phir_age_from_dob, None)

            if error:
                # PSC1
                worksheet.write_string(row, 0, psc1)
                # ACE-IQ
                worksheet.write(row, 1, col_1[0], col_1[1])
                worksheet.write(row, 2, col_2[0], col_2[1])
                worksheet.write(row, 3, col_3[0], col_3[1])
                # PHIR
                worksheet.write(row, 4, col_4[0], col_4[1])
                worksheet.write(row, 5, col_5[0], col_5[1])
                row += 1

    workbook.close()


if __name__ == "__main__":
    main()
