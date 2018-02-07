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

import csv
from datetime import datetime

import logging
logger = logging.getLogger(__name__)


def _parse_trial(trial, trial_result, questions=None):
    if questions:
        if trial in questions:
            trial_type = questions[trial]
            if trial_type == 'datetime.date':
                date_format = '%d-%m-%Y'
                try:
                    return datetime.strptime(trial_result, date_format).date()
                except ValueError:
                    logger.error('cannot parse trial result as a date: %s',
                                trial_result)
            elif trial_type == 'int':
                try:
                    return int(trial_result)
                except ValueError:
                    logger.error('cannot parse trial result as an integer: %s',
                                trial_result)
            else:  # fall back to plain string
                return trial_result
        return None
    return trial_result


def _add_trial_result(result, psc1, age_band, iteration, trial, trial_result):
    psc1_value = result.setdefault(psc1, {})
    age_band_value = psc1_value.setdefault(age_band, {})
    trial_value = age_band_value.setdefault(trial, {})
    trial_value[iteration] = trial_result  # overwrite previous occurrences
    return result


def _add_age_band_timestamp(timestamps, psc1, age_band, timestamp):
    psc1_value = timestamps.setdefault(psc1, {})
    timestamp_range = psc1_value.setdefault(age_band, [datetime.max, datetime.min])
    if timestamp < timestamp_range[0]:
        timestamp_range[0] = timestamp
    if timestamp > timestamp_range[1]:
        timestamp_range[1] = timestamp
    return timestamp_range


def read_psytools(path, questions=None):
    """
    Read a Psytools questionnaire exported in CSV format

    The 'User code' columns combines the PSC1 subject identifier and
    the administered version of the questionnaire, one version for each
    age band C1, C2 and C3. A 'User code' looks like 110001234567-C2.

    A participant may be erroneously administered the same questionnaire for
    each possible age band, for example as 110001234567-C1, 110001234567-C2
    and  110001234567-C3. The disambiguation policy suggested by Delosis is
    to keep the most recent.

    We record the 'Completed timestamp' precisely to help find the most recent
    version of the questionnaire, if needed.

    Since users may skip back before moving forward again, we follow the
    algorithm suggested by Delosis: discard trials for which column
    'Response' is 'skip_back'. Also keep only the latest iteration as
    identified by column 'Iteration'.

    The expected outcome for each question is usually found in column 'Trial'.
    """
    result = {}
    timestamps = {}

    with open(path, mode='r') as psytools:
        reader = csv.DictReader(psytools, dialect='excel')
        for row in reader:
            # user code ends with -C1, -C2 or-C3
            # where C1, C2, C3 represent one of the 3 age bands
            code = row['User code']
            if not (len(code) > 3 and code[-3] == '-'):
                logger.info('ill-formed user code: %s', code)
                continue
            psc1 = code[:-3]
            age_band = code[-2:]
            if age_band not in {'C1', 'C2', 'C3'}:
                logger.info('unknown age band: %s', age_band)
                continue
            # skip dummy test subjects
            if len(psc1) != 12 or not psc1.isdigit():
                continue

            # record timestamp range for each age band
            completed = datetime.strptime(row['Completed Timestamp'],
                                          '%Y-%m-%d %H:%M:%S.%f')
            _add_age_band_timestamp(timestamps, psc1, age_band, completed)

            # discard trials that have been skipped back
            response = row['Response']
            if response == 'skip_back':  # mail from John on 2017-01-21
                continue

            # discard empty 'Trial results'
            trial_result = row['Trial result']
            if trial_result == '':
                continue

            trial = row['Trial']
            iteration = int(row['Iteration'])
            trial_result = _parse_trial(trial, trial_result, questions)
            if trial_result:
                _add_trial_result(result, psc1, age_band, iteration, trial, trial_result)

    # clean up multiple age bands and iterations
    for psc1, psc1_value in result.items():
        if len(psc1_value) > 1:
            logger.info('multiple age bands: %s', psc1)
        # keep only the most recent age band - mail from John on 2017-03-14
        psc1_value = psc1_value[max(psc1_value.keys(),
                                    key=lambda x: timestamps[psc1][x][1])]
        result[psc1] = psc1_value
        for trial, trial_value in psc1_value.items():
            # keep only the latest iteration - mail from John on 2017-01-21
            trial_value = trial_value[max(trial_value.keys())]
            psc1_value[trial] = trial_value

    return result
