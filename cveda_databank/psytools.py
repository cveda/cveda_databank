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
import datetime


def _init_trial_value(result, psc1, trial):
    psc1_value = result.setdefault(psc1, {})
    trial_value = psc1_value.setdefault(trial, {})
    return trial_value


def read_psytools(path, questions=None):
    result = {}

    with open(path, mode='r') as psytools:
        reader = csv.DictReader(psytools, dialect='excel')
        for row in reader:
            # extract PSC1 from user codes of the form <PSC1>-C3
            psc1 = row['User code']
            if psc1[-3:-1] == '-C' and psc1[-1].isdigit():
                psc1 = psc1[:-3]
            # skip dummy test subjects
            if not (len(psc1) == 12 and psc1.isdigit()):
                continue
            trial_result = row['Trial result']
            if trial_result == 'skip_back':  # mail from John Rogers sent 2017-01-21
                continue
            if trial_result == '':  # empty fields are discarded
                continue
            trial = row['Trial']
            if questions:
                if trial in questions:
                    trial_value = _init_trial_value(result, psc1, trial)
                    iteration = int(row['Iteration'])
                    trial_type = questions[trial]
                    if trial_type == 'datetime.date':
                        date_format = '%d-%m-%Y'
                        trial_value[iteration] = datetime.datetime.strptime(trial_result,
                                                                            date_format).date()
                    elif trial_type == 'int':
                        trial_value[iteration] = int(trial_result)
                    else:
                        trial_value[iteration] = trial_result
            else:
                trial_value = _init_trial_value(result, psc1, trial)
                iteration = int(row['Iteration'])
                trial_value[iteration] = trial_result

    # clean up: keep last iteration only
    for psc1, psc1_value in result.items():
        for trial, trial_value in psc1_value.items():
            psc1_value[trial] = trial_value[max(trial_value.keys())]

    return result
