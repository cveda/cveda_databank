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

import xlsxwriter
# import ../cveda_databank
import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
from cveda_databank import read_psytools

ACE_IQ_PATH = '/cveda/databank/RAW/PSC1/psytools/cVEDA-cVEDA_ACEIQ-BASIC_DIGEST.csv'
PDS_PATH = '/cveda/databank/RAW/PSC1/psytools/cVEDA-cVEDA_PDS-BASIC_DIGEST.csv'
SDIM_PATH = '/cveda/databank/RAW/PSC1/psytools/cVEDA-cVEDA_SDIM-BASIC_DIGEST.csv'


def main():
    # ACE-IQ questionnaire
    ace_iq_questions = {'ACEIQ_C1': None}
    ace_iq = read_psytools(ACE_IQ_PATH, ace_iq_questions)
    # PDS questionnaire
    pds_questions = {'PDS_gender': None}
    pds = read_psytools(PDS_PATH, pds_questions)
    # SDIM questionnaire
    sdim_questions = {'SDI_02': None}
    sdim = read_psytools(SDIM_PATH, sdim_questions)

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
    worksheet.merge_range(0, 1, 1, 1, u'ACE-IQ', HEADER_FORMAT)
    worksheet.set_column(1, 1, 12)
    # PDS
    worksheet.merge_range(0, 2, 1, 2, u'PDS', HEADER_FORMAT)
    worksheet.set_column(2, 2, 12)
    # SDIM
    worksheet.merge_range(0, 3, 1, 3, u'SDIM', HEADER_FORMAT)
    worksheet.set_column(3, 3, 12)
    # more formatting and prepare for writing data
    worksheet.freeze_panes(2, 0)
    error_format = {'bg_color': '#FF6A6A'}
    ERROR_FORMAT = workbook.add_format(error_format)
    row = 2

    for psc1 in ace_iq.keys() & pds.keys() & sdim.keys():
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

        if psc1.startswith('1'):
            if len(merge) > 1:
                # PSC1
                worksheet.write_string(row, 0, psc1)
                # ACE-IQ
                if ace_iq_sex and (merge[ace_iq_sex] != max(merge.values()) or
                                   merge[ace_iq_sex] == min(merge.values())):
                    worksheet.write(row, 1, ace_iq_sex, ERROR_FORMAT)
                else:
                    worksheet.write(row, 1, ace_iq_sex)
                # PDS
                if pds_sex and (merge[pds_sex] != max(merge.values()) or
                                merge[pds_sex] == min(merge.values())):
                    worksheet.write(row, 2, pds_sex, ERROR_FORMAT)
                else:
                    worksheet.write(row, 2, pds_sex)
                # SDIM
                if sdim_sex and (merge[sdim_sex] != max(merge.values()) or
                                 merge[sdim_sex] == min(merge.values())):
                    worksheet.write(row, 3, sdim_sex, ERROR_FORMAT)
                else:
                    worksheet.write(row, 3, sdim_sex)
                row += 1

    workbook.close()


if __name__ == "__main__":
    main()
