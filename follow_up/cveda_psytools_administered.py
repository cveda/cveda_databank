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
from csv import DictWriter
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



def _extract_timestamps(psc1_path):
    """Extract from a Psytools file a summary of timestamps
    for each PSC1 code and age band.

    Parameters
    ----------
    psc1_path: str
        Input: PSC1-encoded Psytools file.

    """
    result = {}

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
    """Extract a summary of timestamps for each PSC1 code
    from all psytools questionnaires within a directory.

    Parameters
    ----------
    psc1_dir: str
        Input directory with PSC1-encoded questionnaires.

    """
    result = {}

    for psc1_file in os.listdir(psc1_dir):
        psc1_path = os.path.join(psc1_dir, psc1_file)
        timestamps = _extract_timestamps(psc1_path)
        for psc1, value in timestamps.items():
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
            timestamps[psc1] = {
                'age_band': age_band,
                'completed': value[age_band]['completed'],
                'processed': value[age_band]['processed'],
            }

        questionnaire = psc1_file
        prefix = 'cVEDA-cVEDA_'
        if psc1_file.startswith(prefix):
            questionnaire = psc1_file[len(prefix):]
        questionnaire = questionnaire.rsplit('-', 1)[0]

        result[questionnaire] = timestamps

    return result


def main():
    psytools = extract_timestamps(PSYTOOLS_PSC1_DIR)

    reshape = {}
    for questionnaire, timestamps in psytools.items():
        for psc1, timestamp in timestamps.items():
            reshape.setdefault(psc1, {})[questionnaire] = {
                'completed': timestamp['completed'],
                'processed': timestamp['processed'],
            }

    header = ['PSC1']
    header.extend(sorted(psytools.keys()))
    header.append('Completed min/max gap')
    header.append('Completed/Processed gap')
    print(', '.join(header))
    for psc1, questionnaires in reshape.items():
        row = [psc1]
        grand_completed_min, grand_completed_max = datetime.max, datetime.min
        grand_processing_gap = 0
        for q in sorted(psytools.keys()):
            if q in questionnaires:
                completed_min, completed_max = questionnaires[q]['completed']
                grand_completed_min = min(completed_min, grand_completed_min)
                grand_completed_max = max(completed_max, grand_completed_max)
                processed_min, processed_max = questionnaires[q]['processed']
                if completed_min.date() != completed_max.date():
                    row.append('/'.join((completed_min.strftime('%Y-%m-%d'),
                                         completed_max.strftime('%Y-%m-%d'))))
                else:
                    row.append(completed_max.strftime('%Y-%m-%d'))
                processing_gap = (processed_max - completed_max).days
                if processing_gap > abs(grand_processing_gap):
                    grand_processing_gap = processing_gap 
            else:
                row.append('')
        row.append(str((grand_completed_max - grand_completed_min).days))
        row.append(str(grand_processing_gap))
        print(', '.join(row))


if __name__ == "__main__":
    main()
