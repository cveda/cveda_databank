#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018 CEA
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
import os
from cveda_databank import PSC2_FROM_PSC1
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# frozen PSC1 codes
_EXCEL_FREEZE_FILE = '/cveda/databank/framework/meta_data/freeze/1.0/cVEDA_PSC_Data_Freeze.xlsx'

# in/out paths
_IN_PATH = '/cveda/databank/processed/psytools'
_OUT_PATH = '/cveda/databank/PUBLICATION/1.2/psytools'


def read_freeze(path):
    with pandas.ExcelFile(path) as excel_file:
        converters = {
            'PSC1': str,
        }
        df = pandas.read_excel(path, converters=converters)
        return df['PSC1'].tolist()


def read_psc1_codes(files):
    result = []
    for path in files:
        with open(path) as f:
            for line in f:
                result.append(line.strip())
    return result


def main():
    # frozen participants
    frozen = set(PSC2_FROM_PSC1[psc1] for psc1
                 in read_freeze(_EXCEL_FREEZE_FILE))

    # keep only frozen participants
    for psytools in os.listdir(_IN_PATH):
        if '_FU1-' in psytools:
            continue  # only baseline (BL) for 1.1
        inpath = os.path.join(_IN_PATH, psytools)
        outpath = os.path.join(_OUT_PATH, psytools)
        with open(inpath, 'r') as infile, open(outpath, 'w') as outfile:
            line = next(infile)
            outfile.write(line)
            for line in infile:
                psc2 = line[:12]
                if psc2 in frozen:
                    outfile.write(line)


if __name__ == "__main__":
    main()
