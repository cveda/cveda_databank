#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018-2019 CEA
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


from cveda_databank import PSC2_FROM_PSC1, DOB_FROM_PSC1
from cveda_databank.core import _read_recruitment_files
import os
from dateutil.relativedelta import relativedelta
from pandas import isnull

import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger()


# recruitment file with reference information
_RECRUITMENT_FILES_DIR = '/cveda/databank/framework/meta_data/recruitment_files'
_RECRUITMENT_FILES = (
    'recruitment_file_PGIMER_2019-04-30.xlsx',
    'recruitment_file_IMPHAL_2019-06-06.xlsx',
    'recruitment_file_KOLKATA_2019-06-06.xlsx',
    'recruitment_file_RISHIVALLEY_2019-06-06.xlsx',
    'recruitment_file_MYSORE_2019-06-06.xlsx',
    'recruitment_file_NIMHANS_2019-06-06.xlsx',
    'recruitment_file_SJRI_2019-06-06.xlsx',
)

_FOLLOW_UP_FILES = {
    'FU1': '/cveda/framework/meta_data/freeze/1.1/follow_up_1.txt',
    'FU2': '/cveda/framework/meta_data/freeze/1.1/follow_up_2.txt',
}

_RECRUITMENT_CENTRE = {
    '11': 'PGIMER',
    '12': 'IMPHAL',
    '13': 'KOLKATA',
    '14': 'RISHIVALLEY',
    '15': 'MYSORE',
    '16': 'NIMHANS',
    '17': 'SJRI',
}


def main():
    recruitment_data = _read_recruitment_files(os.path.join(_RECRUITMENT_FILES_DIR, f)
                                               for f in _RECRUITMENT_FILES)

    # rename columns with spaces
    recruitment_data.columns = [c.replace(' ', '_')
                                for c in recruitment_data.columns]

    follow_up = {}
    for time_point, path in _FOLLOW_UP_FILES.items():
        with open(path) as f:
            follow_up[time_point] = set(line.strip() for line in f)

    print(','.join(('PSC2', 'recruitment centre', 'sex', 'age band',
                    'baseline assessment age', 'baseline assessment age in days',
                    'baseline MRI scan age', 'baseline MRI scan age in days',
                     'follow up')))
    for row in recruitment_data.itertuples(index=False):
        psc1 = row.PSC1
        site = psc1[:2]

        if psc1 in PSC2_FROM_PSC1:
            psc2 = PSC2_FROM_PSC1[psc1]
        else:
            logger.error('%s: invalid PSC1 code in recruitment file', psc1)
            psc2 = None

        if row.SEX not in {'F', 'M'}:
            logger.error('%s: invalid value for sex: "%s"', psc1, row.SEX)
            sex = None
        else:
            sex = row.SEX

        age_band = row.Age_band
        if age_band not in {'C1', 'C2', 'C3'}:
            logger.error('%s: invalid value for age band: "%s"',
                         psc1, row[4])
            age_band = None

        baseline_age = None
        baseline_age_days = None
        baseline_date = row.Base_line_assessment_date
        baseline_date = baseline_date.date()
        if psc1 in DOB_FROM_PSC1:
            baseline_age = relativedelta(baseline_date, DOB_FROM_PSC1[psc1]).years
            baseline_age_days = (baseline_date - DOB_FROM_PSC1[psc1]).days

        for time_point, participants in follow_up.items():
            if psc2 in participants:
                break
        else:
            logger.warning('%s: not in follow up', psc1)
            time_point = None

        baseline_mri_age = None
        baseline_mri_age_days = None
        if 'MRI_date' in recruitment_data.columns:  # some centres don't do MRI
            baseline_mri_date = row.MRI_date
            if not isnull(baseline_mri_date) and psc1 in DOB_FROM_PSC1:
                baseline_mri_date = baseline_mri_date.date()
                baseline_mri_age = relativedelta(baseline_mri_date, DOB_FROM_PSC1[psc1]).years
                baseline_mri_age_days = (baseline_mri_date - DOB_FROM_PSC1[psc1]).days

        if psc2:
            print(','.join((psc2,
                            _RECRUITMENT_CENTRE[site],
                            '' if sex is None else sex,
                            '' if age_band is None else age_band,
                            '' if baseline_age is None else str(baseline_age),
                            '' if baseline_age is None else str(baseline_age_days),
                            '' if baseline_mri_age is None else str(baseline_mri_age),
                            '' if baseline_mri_age is None else str(baseline_mri_age_days),
                            '' if time_point is None else time_point)))


if __name__ == "__main__":
    main()
