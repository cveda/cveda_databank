#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2017-2019 CEA
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


import pandas
from datetime import datetime
from dateutil.relativedelta import relativedelta
from random import shuffle
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# reference file for date of birth, sex, date of baseline assessment
_EXCEL_RECRUITMENT_FILE = '/cveda/databank/framework/meta_data/follow_up/randomization_2019/Recruitment_file_3rd_randomization.xlsx'

# participants already scheduled for follow-up in 2017 and 2018
_EXCEL_FOLLOW_UP = {
    'FU1_2017': '/cveda/databank/framework/meta_data/follow_up/randomization_2017/follow_up_1_2017-12-21.xlsx',
    'FU2_2017': '/cveda/databank/framework/meta_data/follow_up/randomization_2017/follow_up_2_2017-12-21.xlsx',
    'IMPHAL_FU1_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_IMPHAL_1_2018-10-22.xlsx',
    'IMPHAL_FU2_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_IMPHAL_2_2018-10-22.xlsx',
    'KOLKATA_FU1_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_KOLKATA_1_2018-10-22.xlsx',
    'KOLKATA_FU2_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_KOLKATA_2_2018-10-22.xlsx',
    'MYSORE_FU1_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_MYSORE_1_2018-10-22.xlsx',
    'MYSORE_FU2_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_MYSORE_2_2018-10-22.xlsx',
    'NIMHANS_FU1_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_NIMHANS_1_2018-10-22.xlsx',
    'NIMHANS_FU2_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_NIMHANS_2_2018-10-22.xlsx',
    'PGIMER_FU1_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_PGIMER_1_2018-10-22.xlsx',
    'PGIMER_FU2_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_PGIMER_2_2018-10-22.xlsx',
    'RISHI_VALLEY_FU1_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_RISHI_VALLEY_1_2018-10-22.xlsx',
    'RISHI_VALLEY_FU2_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_RISHI_VALLEY_2_2018-10-22.xlsx',
    'SJRI_FU1_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_SJRI_1_2018-10-22.xlsx',
    'SJRI_FU2_2018': '/cveda/databank/framework/meta_data/follow_up/randomization_2018/follow_up_SJRI_2_2018-10-22.xlsx',
}

# valid PSC1 codes
_PSC1_CODES = (
    '/cveda/databank/framework/psc/PSC1_PGIMER_2016-07-05.txt',
    '/cveda/databank/framework/psc/PSC1_IMPHAL_2016-07-05.txt',
    '/cveda/databank/framework/psc/PSC1_KOLKATA_2016-07-05.txt',
    '/cveda/databank/framework/psc/PSC1_RISHIVALLEY_2016-07-05.txt',
    '/cveda/databank/framework/psc/PSC1_MYSORE_2016-07-05.txt',
    '/cveda/databank/framework/psc/PSC1_NIMHANS_2016-07-05.txt',
    '/cveda/databank/framework/psc/PSC1_SJRI_2016-07-05.txt',
    '/cveda/databank/framework/psc/PSC1_PGIMER_2018-06-23.txt',
    '/cveda/databank/framework/psc/PSC1_IMPHAL_2018-06-23.txt',
    '/cveda/databank/framework/psc/PSC1_MYSORE_2018-06-23.txt',
    '/cveda/databank/framework/psc/PSC1_NIMHANS_2018-06-23.txt',
)

_AGE_BAND = {
    'C1': 1,
    'C2': 2,
    'C3': 3,
}


def _age_band(age_in_years):
    # As documented here: https://github.com/cveda/cveda_databank/wiki
    #   C1:  6-11
    #   C2: 12-17
    #   C3: 18-23
    # The few subjects < 6 and > 23 end up in C1 and C3 respectively.
    if age_in_years < 12:
        return 1
    elif age_in_years < 18:
        return 2
    else:
        return 3


def _time_block(d):
    # Ensure that we don't get all the people in the first follow up
    # coming from the same part of the year.
    if d.month in {11, 12, 1}:
        return 1
    elif d.month in {2, 3, 4}:
        return 2
    elif d.month in {5, 6, 7}:
        return 3
    else:  # if d.month in {8, 9, 10}
        return 4


def read_previous_randomization(files):
    result = []
    for time_point, path in files.items():
        with pandas.ExcelFile(path) as excel_file:
            converters = {'PSC1': str}
            # sheet_name not available prior to 0.21.0, use sheetname instead
            sheets = pandas.read_excel(excel_file, sheetname=None,
                                       converters=converters)
            for df in sheets.values():
                result.append(df)
    return pandas.concat(result, ignore_index=True)


def read_recruitment_files(path):
    result = {}
    with pandas.ExcelFile(path) as excel_file:
        converters = {
            'PSC1': str,
            'Base line age': int,
            'Correct Age': int,
            'Correct age': int,
            'Age diff': int,
            'Age at Scan': int,
        }
        for center in excel_file.sheet_names:
            # read only 1st sheet if additional sheets have crept in
            result[center] = pandas.read_excel(path, sheetname=center,
                                               converters=converters)
    return result


def read_psc1_codes(files):
    result = []
    for path in files:
        with open(path) as f:
            for line in f:
                result.append(line.strip())
    return result


def randomize(data):
    follow_ups = ({}, {})  # follow-up 1 and follow-up 2

    for calculated_band, sexes in data.items():
        for sex, time_blocks in sexes.items():
            for time_block, participants in time_blocks.items():
                psc1s = list(participants.keys())
                # Randomly split each gpoup in half.
                half_len = len(psc1s) // 2
                shuffle(psc1s)
                partition = [psc1s[:half_len], psc1s[half_len:]]
                shuffle(partition)
                for i in (0, 1):  # follow-up 1 and follow-up 2
                    follow_ups[i].update([(psc1, participants[psc1])
                                          for psc1 in partition[i]])

    return follow_ups


def main():
    # read all sources of data
    previous = read_previous_randomization(_EXCEL_FOLLOW_UP)
    previous_psc1 = {cell for cell in previous['PSC1']}
    recruitment = read_recruitment_files(_EXCEL_RECRUITMENT_FILE)
    df = pandas.concat((df for df in recruitment.values()),
                       ignore_index=True)
    recruitment_psc1 = {cell for cell in df['PSC1']}
    valid_psc1 = set(read_psc1_codes(_PSC1_CODES))

    # check for basic errors in recruitment files
    for psc1 in (previous_psc1 - recruitment_psc1):
        logger.error('%s: participant previously scheduled for follow-up'
                      ' is missing from recruitment file', psc1)
    for psc1 in (recruitment_psc1 - valid_psc1):
        logger.error('%s: invalid PSC1 code', psc1)

    # process each center
    for center, df in recruitment.items():
        #~ get rid of previously randomized PSC1 codes
        df = df[~df['PSC1'].isin(previous_psc1)]

        data = {}
        seen = set()  # detect duplicates

        for row in df.itertuples(index=False, name=None):
            # PSC1
            psc1 = row[0]
            if psc1 in seen:
                logger.error('%s: duplicate PSC1', psc1)
                continue
            else:
                seen.add(psc1)

            # DOB
            dob = row[1]
            if pandas.isnull(dob):
                logger.error('%s: date of birth is missing', psc1)
                continue
            dob = dob.date()  # pandas.Timestamp → datetime.date

            # SEX
            sex = str(row[2])
            if len(sex) > 1:
                logger.warning('%s: sex is more than 1 character (%s)',
                                psc1, sex)
                sex = sex.strip()
            if sex not in {'F', 'M'}:
                logger.error('%s: sex is undefined', psc1)
                continue

            # Base line Assessment date
            baseline = row[5]
            if pandas.isnull(baseline):
                logger.error('%s: baseline assessment date is missing', psc1)
                continue
            baseline = baseline.date()  # pandas.Timestamp → datetime.date

            # define the time-block of assessment date
            time_block = _time_block(baseline)

            # calculate theoretical age band at baseline
            calculated_age = relativedelta(baseline, dob).years
            calculated_band = _age_band(calculated_age)

            data.setdefault(calculated_band, {}) \
                .setdefault(sex, {}) \
                .setdefault(time_block, {})[psc1] = (dob, sex, baseline)

        follow_ups = randomize(data)

        # prepare output DataFrame
        for i in (1, 2):  # follow-ups 1 and 2 years later
            data = []
            # sort participants by follow-up date
            for psc1, (dob, sex, baseline) in sorted(follow_ups[i-1].items(),
                                                     key=lambda x: x[1][2]):
                # follow-up assessment date: 1 or 2 years later
                follow_up = baseline + relativedelta(years=i)
                age = relativedelta(follow_up, dob).years
                age_band = _age_band(age)
                calendar_month = follow_up.strftime('%B %Y')
                # complete row for subject
                data.append((calendar_month, baseline,
                             psc1, dob, sex,
                             age, 'C{}'.format(age_band)))
            columns = (
                'Follow-up assessment month', 'Baseline assessment date',
                'PSC1', 'Date of Birth', 'Sex',
                'Planned age', 'Planned age band (theoretical)',
            )
            df = pandas.DataFrame.from_records(data, columns=columns)

            # write DataFrame to Excel file
            today = datetime.now().strftime('%Y-%m-%d')
            path = 'follow_up_{}_{}_{}.xlsx'.format(center, i, today)
            with pandas.ExcelWriter(path) as excel_writer:
                df.to_excel(excel_writer,
                            sheet_name=center,
                            header=True,
                            index=False)


if __name__ == "__main__":
    main()
