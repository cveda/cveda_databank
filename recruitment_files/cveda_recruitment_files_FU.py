#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2021 CEA
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
import os
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
import pandas

import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger()


# recruitment file with reference information
_RECRUITMENT_FILES_DIR = '/cveda/databank/framework/meta_data/recruitment/FU'
_RECRUITMENT_FILES = (
    'cVEDA_FU_record.csv',
)

_RECRUITMENT_CENTRE = {
    '11': 'PGIMER',
    '12': 'IMPHAL',
    '13': 'KOLKATA',
    '14': 'RISHIVALLEY',
    '15': 'MYSORE',
    '16': 'NIMHANS',
    '17': 'SJRI',
}


def _age_converter(s):
    if s:
        return int(s)
    else:
        return -1


def _date_converter(s):
    if s:
        return parse(s).date()
    else:
        return None


def _read_recruitment_fu_file(path):
    converters = {
        'PSC': str,
        'FU assessment date': _date_converter,
        'Age at FU': _age_converter,
        'MRI Date': _date_converter,
        'Age at MRI': _age_converter,
        'Assessment': str,
    }
    return pandas.read_csv(path, converters=converters, skipinitialspace=True)


def _read_recruitment_fu_files(paths):
    return pandas.concat((_read_recruitment_fu_file(path) for path in paths),
                         ignore_index=True, sort=False)


def main():
    recruitment_data = _read_recruitment_fu_files(os.path.join(_RECRUITMENT_FILES_DIR, f)
                                                  for f in _RECRUITMENT_FILES)

    print(','.join(('PSC2', 'recruitment centre',
                    'follow up',
                    'assessment age', 'assessment age in days',
                    'MRI scan age', 'MRI scan age in days',
                    'assessment')))
    for row in recruitment_data.itertuples(index=False):
        psc1 = row.PSC
        site = psc1[:2]

        if psc1 in PSC2_FROM_PSC1:
            psc2 = PSC2_FROM_PSC1[psc1]
        else:
            logger.error('%s: invalid PSC1 code in recruitment file', psc1)
            psc2 = None

        follow_up_group = row._1

        follow_up_age = None
        follow_up_age_days = None
        follow_up_date = row._2
        follow_up_age = row._3
        # ~ print("{} - {}".format(type(follow_up_date), type(follow_up_age)))
        if psc1 in DOB_FROM_PSC1:
            follow_up_age_2 = relativedelta(follow_up_date, DOB_FROM_PSC1[psc1]).years
            follow_up_age_days = (follow_up_date - DOB_FROM_PSC1[psc1]).days
            if (follow_up_age_2 != follow_up_age):
                logger.error('%s: inconsistent ages: %d-%d', psc1, follow_up_age, follow_up_age_2)

        follow_up_mri_age = None
        follow_up_mri_age_days = None
        follow_up_mri_date = row._4
        follow_up_mri_age = row._5
        if not pandas.isnull(follow_up_mri_date) and psc1 in DOB_FROM_PSC1:
            # ~ print("{} - {}".format(type(follow_up_mri_date), type(follow_up_mri_age)))
            follow_up_mri_age_2 = relativedelta(follow_up_mri_date, DOB_FROM_PSC1[psc1]).years
            follow_up_mri_age_days = (follow_up_mri_date - DOB_FROM_PSC1[psc1]).days
            if (follow_up_mri_age_2 != follow_up_mri_age):
                logger.error('%s: inconsistent ages: %d-%d', psc1, follow_up_mri_age, follow_up_mri_age_2)

        if psc2:
            print(','.join((psc2,
                            _RECRUITMENT_CENTRE[site],
                            '' if follow_up_group is None else follow_up_group,
                            '' if follow_up_age < 0 else str(follow_up_age),
                            '' if follow_up_age_days is None else str(follow_up_age_days),
                            '' if follow_up_mri_age < 0 else str(follow_up_mri_age),
                            '' if follow_up_mri_age_days is None else str(follow_up_mri_age_days),
                            row.Assessment)))


if __name__ == "__main__":
    main()
