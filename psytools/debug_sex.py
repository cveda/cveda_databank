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

ACE_IQ : str
    ACE-IQ questionnaire as exported from the Delosis server as a CSV file.

PDS : str
    PDS questionnaire as exported from the Delosis server as a CSV file.

SDIM : str
    SDIM questionnaire as exported from the Delosis server as a CSV file.

"""

import csv
import sys
import datetime
import xlsxwriter

ACE_IQ = '/cveda/databank/BL/RAW/PSC1/psytools/cVEDA-cVEDA_ACEIQ-BASIC_DIGEST.csv'
PDS = '/cveda/databank/BL/RAW/PSC1/psytools/cVEDA-cVEDA_PDS-BASIC_DIGEST.csv'
SDIM = '/cveda/databank/BL/RAW/PSC1/psytools/cVEDA-cVEDA_SDIM-BASIC_DIGEST.csv'


def read_ace_iq(path):
    ace_iq = {}
    with open(path, mode='r', newline='') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(4096))
        csvfile.seek(0)
        reader = csv.DictReader(csvfile, dialect=dialect)
        for row in reader:
            trial = row['Trial']
            if trial == 'ACEIQ_C1':
                psc1 = row['User code']
                if psc1[-3:-1] == '-C':  # user code ID of the form <PSC1>-C1, <PSC1>-C3, etc.
                    psc1 = psc1[:-3]
                result = row['Trial result']
                if result != 'skip_back':
                    psc1_value = ace_iq.setdefault(psc1, {})
                    iteration = int(row['Iteration'])
                    iteration_value = psc1_value.setdefault(iteration, {})
                    result = row['Trial result']
                    if result not in {'', 'refuse'}:
                        if result in {'F', 'M'}:
                            iteration_value['sex'] = result
                        else:
                            print('subject {} has unexpected sex "{}"'.format(psc1, result))
    for psc1, value in ace_iq.items():
        ace_iq[psc1] = value[max(value.keys())]  # keep last iteration only
    return ace_iq


def read_pds(path):
    pds = {}
    with open(path, mode='r', newline='') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(4096))
        csvfile.seek(0)
        reader = csv.DictReader(csvfile, dialect=dialect)
        for row in reader:
            trial = row['Trial']
            if trial == 'PDS_gender':
                psc1 = row['User code']
                if psc1[-3:-1] == '-C':  # user code ID of the form <PSC1>-C1, <PSC1>-C3, etc.
                    psc1 = psc1[:-3]
                result = row['Trial result']
                if result != 'skip_back':
                    psc1_value = pds.setdefault(psc1, {})
                    iteration = int(row['Iteration'])
                    iteration_value = psc1_value.setdefault(iteration, {})
                    result = row['Trial result']
                    if result not in {'', 'refuse'}:
                        if result in {'F', 'M'}:
                            iteration_value['sex'] = result
                        else:
                            print('subject {} has unexpected sex "{}"'.format(psc1, result))
    for psc1, value in pds.items():
        pds[psc1] = value[max(value.keys())]  # keep last iteration only
    return pds


def read_sdim(path):
    sdim = {}
    with open(path, mode='r', newline='') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(4096))
        csvfile.seek(0)
        reader = csv.DictReader(csvfile, dialect=dialect)
        for row in reader:
            trial = row['Trial']
            if trial == 'SDI_02':
                psc1 = row['User code']
                if psc1[-3:-1] == '-C':  # user code ID of the form <PSC1>-C1, <PSC1>-C3, etc.
                    psc1 = psc1[:-3]
                result = row['Trial result']
                if result != 'skip_back':
                    psc1_value = sdim.setdefault(psc1, {})
                    iteration = int(row['Iteration'])
                    iteration_value = psc1_value.setdefault(iteration, {})
                    result = row['Trial result']
                    if result not in {'', 'refuse'}:
                        if result in {'F', 'M'}:
                            iteration_value['sex'] = result
                        else:
                            print('subject {} has unexpected sex "{}"'.format(psc1, result))
    for psc1, value in sdim.items():
        sdim[psc1] = value[max(value.keys())]  # keep last iteration only
    return sdim



def main():
    # ACE-IQ questionnaire
    ace_iq = read_ace_iq(ACE_IQ)

    # PDS questionnaire
    pds = read_pds(PDS)

    # SDIM questionnaire
    sdim = read_sdim(SDIM)

    # Excel output
    options = {
        'strings_to_numbers': False,
    }
    workbook = xlsxwriter.Workbook('cVEDA_Psytools.xlsx', options)
    HEADER_FORMAT = workbook.add_format({'bold': True,
                                         'align': 'center', 'valign': 'vcenter'})
    worksheet = workbook.add_worksheet('sex')
    # PSC1
    worksheet.merge_range(0, 0, 1, 0, u'PSC1', HEADER_FORMAT)
    worksheet.set_column(0, 0, 14)
    # ACE-IQ
    worksheet.write(0, 1,u'ACE-IQ', HEADER_FORMAT)
    worksheet.write(1, 1, u'sex', HEADER_FORMAT)
    worksheet.set_column(1, 1, 12)
    # PDS
    worksheet.write(0, 2, u'PDS', HEADER_FORMAT)
    worksheet.write(1, 2, u'sex', HEADER_FORMAT)
    worksheet.set_column(2, 2, 12)
    # SDIM
    worksheet.write(0, 3, u'SDIM', HEADER_FORMAT)
    worksheet.write(1, 3, u'sex', HEADER_FORMAT)
    worksheet.set_column(3, 3, 12)
    # more formatting and prepare for writing data
    worksheet.freeze_panes(2, 0)
    error_format = {'bg_color': '#FF6A6A'}
    ERROR_FORMAT = workbook.add_format(error_format)
    row = 2

    for psc1 in ace_iq.keys() & pds.keys() & sdim.keys():
        total = {}
        if psc1 in ace_iq and 'sex' in ace_iq[psc1]:
            ace_iq_sex = ace_iq[psc1]['sex']
            total[ace_iq_sex] = total.setdefault(ace_iq_sex, 0) + 1
        else:
            ace_iq_sex = None
        if psc1 in pds and 'sex' in pds[psc1]:
            pds_sex = pds[psc1]['sex']
            total[pds_sex] = total.setdefault(pds_sex, 0) + 1
        else:
            pds_sex = None
        if psc1 in sdim and 'sex' in sdim[psc1]:
            sdim_sex = sdim[psc1]['sex']
            total[sdim_sex] = total.setdefault(sdim_sex, 0) + 1
        else:
            sdim_sex = None

        if psc1.startswith('1'):
            if len(total) != 1:
                # PSC1
                worksheet.write_string(row, 0, psc1)
                # ACE-IQ
                if ace_iq_sex and (total[ace_iq_sex] != max(total.values()) or
                                   total[ace_iq_sex] == min(total.values())):
                    worksheet.write(row, 1, ace_iq_sex, ERROR_FORMAT)
                else:
                    worksheet.write(row, 1, ace_iq_sex)
                # PDS
                if pds_sex and (total[pds_sex] != max(total.values()) or
                                total[pds_sex] == min(total.values())):
                    worksheet.write(row, 2, pds_sex, ERROR_FORMAT)
                else:
                    worksheet.write(row, 2, pds_sex)
                # SDIM
                if sdim_sex and (total[sdim_sex] != max(total.values()) or
                                 total[sdim_sex] == min(total.values())):
                    worksheet.write(row, 3, sdim_sex, ERROR_FORMAT)
                else:
                    worksheet.write(row, 3, sdim_sex)
                row += 1

    workbook.close()


if __name__ == "__main__":
    main()
