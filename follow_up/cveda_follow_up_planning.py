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

"""Plan follow up assessments based on information from the baseline Psytools.

This script iterates over Psytools CSV files downloaded from the Delosis
server. For each file it will:
* find the proper age band (most recent 'Completed timestamp') for each PSC1 code,
* find the min and max 'Completed timestamp' and 'Processed timestamp' for each PSC1 code,
* ...

==========
Attributes
==========

Input
-----

PSYTOOLS_PSC1_DIR : str
    Source directory to read PSC1-encoded Psytools files from.

Output
------

"""
import os
from csv import DictReader
from datetime import datetime

import logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger()

# import ../cveda_databank
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
from cveda_databank import read_psytools
from cveda_databank import age_band as cveda_age_band
from cveda_databank import PSC2_FROM_PSC1
from cveda_databank import DOB_FROM_PSC1


PSYTOOLS_PSC1_DIR = '/cveda/databank/RAW/PSC1/psytools'


def _sex_from_psc1(ace_iq_path, pds_path, sdim_path):
    result = {}

    # ACE-IQ questionnaire
    ace_iq_questions = {'ACEIQ_C1': None}
    ace_iq = read_psytools(ace_iq_path, ace_iq_questions)
    # PDS questionnaire
    pds_questions = {'PDS_gender': None}
    pds = read_psytools(pds_path, pds_questions)
    # SDIM questionnaire
    sdim_questions = {'SDI_02': None}
    sdim = read_psytools(sdim_path, sdim_questions)

    for psc1 in ace_iq.keys() | pds.keys() | sdim.keys():
        # skip test entries
        u = psc1.upper()
        if ('DEMO' in u or 'MOCK' in u or 'NPPILOT' in u or 'TEST' in u):
            continue

        # count occurrences of 'F' and 'M'
        f = []
        m = []
        if psc1 in ace_iq and 'ACEIQ_C1' in ace_iq[psc1]:
            ace_iq_sex = ace_iq[psc1]['ACEIQ_C1']
            if ace_iq_sex == "F":
                f.append('ACEIQ_C1')
            else:
                m.append('ACEIQ_C1')
        if psc1 in pds and 'PDS_gender' in pds[psc1]:
            pds_sex = pds[psc1]['PDS_gender']
            if pds_sex == "F":
                f.append('PDS_gender')
            else:
                m.append('PDS_gender')
        if psc1 in sdim and 'SDI_02' in sdim[psc1]:
            sdim_sex = sdim[psc1]['SDI_02']
            if sdim_sex == "F":
                f.append('SDI_02')
            else:
                m.append('SDI_02')

        if len(f) > len(m):
            result[psc1] = 'F'
        elif len(m) > len(f):
            result[psc1] = 'M'

    return result


def _extract_timestamps(psc1_path, result):
    """Extract from a Psytools file a summary of timestamps
    for each PSC1 code and age band.

    Parameters
    ----------
    psc1_path: str
        Input: PSC1-encoded Psytools file.

    result: dict
        Input/Output: for each PSC1 code and age band, provide
        min and max of 'Completed' and 'Processed' timestamps.

    """
    with open(psc1_path, 'r') as psc1_file:
        psc1_reader = DictReader(psc1_file, dialect='excel')

        # read header
        psc1_reader.fieldnames

        # read data
        for row in psc1_reader:
            # subject ID is PSC1 followed by either of:
            #   -C1  age band 6-11
            #   -C2  age band 12-17
            #   -C3  age band 18-23
            psc1_suffix = row['User code'].rsplit('-', 1)
            psc1 = psc1_suffix[0]
            if psc1 in PSC2_FROM_PSC1:
                age_band = psc1_suffix[1]
            else:
                u = psc1.upper()
                if ('DEMO' in u or 'MOCK' in u or 'NPPILOT' in u or
                        'TEST' in u):
                    logging.debug('skipping test subject %s',
                                  row['User code'])
                else:
                    logging.error('unknown PSC1 code %s in user code %s',
                                  psc1, row['User code'])
                continue

            # acquisition time stamp
            # depends on acquisition laptop clock - might be wrong
            completed = datetime.strptime(row['Completed Timestamp'],
                                          '%Y-%m-%d %H:%M:%S.%f')
            completed_min, completed_max = result.setdefault(psc1, {}).setdefault(age_band, {}).setdefault('completed', (datetime.max, datetime.min))
            completed_min = min(completed_min, completed)
            completed_max = max(completed_max, completed)
            result[psc1][age_band]['completed'] = (completed_min, completed_max)

            # transfer to Delosis server time stamp
            # depends on server clock - precise but might occur days after acquisition
            processed = datetime.strptime(row['Processed Timestamp'],
                                          '%Y-%m-%d %H:%M:%S.%f')
            processed_min, processed_max = result.setdefault(psc1, {}).setdefault(age_band, {}).setdefault('processed', (datetime.max, datetime.min))
            processed_min = min(processed_min, processed)
            processed_max = max(processed_max, processed)
            result[psc1][age_band]['processed'] = (processed_min, processed_max)

    return result


def extract_timestamps(psc1_dir):
    """Anonymize and re-encode all psytools questionnaires within a directory.

    PSC1-encoded files are read from `master_dir`, anoymized and converted
    from PSC1 codes to PSC2, and the result is written in `psc2_dir`.

    Parameters
    ----------
    psc1_dir: str
        Input directory with PSC1-encoded questionnaires.

    """
    result = {}

    for psc1_file in os.listdir(psc1_dir):
        psc1_path = os.path.join(psc1_dir, psc1_file)
        _extract_timestamps(psc1_path, result)

    for psc1, value in result.items():
        if len(value) > 1:
            # keep the most recent assessment / age band
            # identified by the largest 'Completed' timestamp
            age_band = max(value.keys(),
                           key=lambda k: value[k]['completed'][1])
            logger.info('%s: selected age band %s over %s',
                        psc1, age_band,
                        '/'.join(x for x in value.keys() if x != age_band))
        else:
            age_band = next(iter(value))  # single key / age band
            logger.debug('%s: using single age band %s', psc1, age_band)

        # repack result using the unique or most recent age band
        result[psc1] = {
            'age_band': age_band,
            'completed': value[age_band]['completed'],
            'processed': value[age_band]['processed'],
        }

    return result


def main():
    psytools = extract_timestamps(PSYTOOLS_PSC1_DIR)

    SEX_FROM_PSC1 = _sex_from_psc1(os.path.join(PSYTOOLS_PSC1_DIR,
                                                'cVEDA-cVEDA_ACEIQ-BASIC_DIGEST.csv'),
                                   os.path.join(PSYTOOLS_PSC1_DIR,
                                                'cVEDA-cVEDA_PDS-BASIC_DIGEST.csv'),
                                   os.path.join(PSYTOOLS_PSC1_DIR,
                                                'cVEDA-cVEDA_SDIM-BASIC_DIGEST.csv'))

    result = []

    for psc1, timestamps in psytools.items():
        age_band = timestamps['age_band']
        completed_min, completed_max = timestamps['completed']
        processed_min, processed_max = timestamps['processed']

        # report Psytools assessments spanning many days
        if completed_min.date() != completed_max.date():
            logger.error('%s: multiple "Completed" timestamps for Psytools assessment (gap of %d days)',
                         psc1, (completed_max.date() - completed_min.date()).days)
        if processed_min.date() != processed_max.date():
            logger.error('%s: multiple "Completed" timestamps for Psytools assessment (gap of %d days)',
                         psc1, (processed_max.date() - processed_min.date()).days)

        # estimate date at baseline Psytools assessment
        time_to_server = processed_max.date() - completed_max.date()
        if time_to_server.days >= 0 and time_to_server.days <= 14:
            baseline = completed_max.date()
        else:
            if time_to_server.days < 0:
                message = '%s: suspect reported date of acquisition (%s) after upload to server (%s)'
            else:
                message = '%s: suspect delay of more than 2 weeks between reported date of acquisition (%s) and upload to server (%s)'
            logger.error(message,
                         psc1,
                         completed_max.strftime('%Y-%m-%d'),
                         processed_max.strftime('%Y-%m-%d'))
            baseline = processed_max.date()

        # "theoretical" age band is calculated by subtracting
        # date of Psytools assessment from date of birth
        if psc1 in DOB_FROM_PSC1:
            birth = DOB_FROM_PSC1[psc1]
            age_in_years = (baseline.year - birth.year -
                            ((baseline.month, baseline.day) <
                             (birth.month, birth.day)))

            # "theoretical" age band at baseline Psytools assessment
            baseline_age_band = cveda_age_band(age_in_years)

            # "theoretical" age band at follow up Psytools assessment 1 year later
            follow_up_age_band = cveda_age_band(age_in_years + 1)

            age_in_years = str(age_in_years)
        else:
            logger.error('%s: unknown age', psc1)
            age_in_years = ''
            baseline_age_band = ''
            follow_up_age_band = ''

        # sex is derived from 3 items in 3 different questionnaires
        if psc1 in SEX_FROM_PSC1:
            sex = SEX_FROM_PSC1[psc1]
        else:
            sex = ''

        result.append((psc1, sex, age_in_years,
                       age_band, baseline_age_band, follow_up_age_band,
                       baseline.strftime('%Y-%m-%d')))

    # sort by date of Psytools baseline assessment
    result.sort(key=lambda x: x[6])

    # print results in CSV format
    print(', '.join(('PSC1', 'sex', 'age',
                     'Psytools age band at baseline',
                     'theoretical age band at baseline',
                     'theoretical age band at follow up',
                     'date of baseline assessment')))
    for x in result:
        print(', '.join(x))


if __name__ == "__main__":
    main()
