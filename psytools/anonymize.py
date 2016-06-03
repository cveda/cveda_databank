#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-encode and anonymize Psytools files.

This script iterates over Psytools CSV files downloaded from the Delosis
server and saved into a directory. For each file it will:
* substitute the PSC1 code for a PSC2 code,
* change acquisition dates into age in days at acquisition.

==========
Attributes
==========

Input
-----

PSYTOOLS_PSC1_DIR : str
    Location of PSC1-encoded Psytools files.

Output
------

PSYTOOLS_PSC2_DIR : str
    Location of PSC2-encoded Psytools files.

"""

PSYTOOLS_PSC1_DIR = '/cveda/BL/RAW/PSC1/psytools'
PSYTOOLS_PSC2_DIR = '/cveda/BL/RAW/PSC2/psytools'

import logging
logging.basicConfig(level=logging.INFO)

import os
from datetime import time
from datetime import datetime

# import ../databank
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
from databank import PSC2_FROM_PSC1
from databank import DOB_FROM_PSC2


def _create_psc2_file(psc1_path, psc2_path):
    """Anonymize and re-encode a Psytools questionnaire from PSC1 to PSC2.

    Parameters
    ----------
    psc1_path: str
        Input: PSC1-encoded Psytools file.
    psc2_path: str
        Output: PSC2-encoded Psytools file.

    """
    with open(psc1_path, 'r') as psc1_file:
        # identify columns to anonymize in header
        header = psc1_file.readline().strip()
        convert = [i for i, field in enumerate(header.split(','))
                   if 'Timestamp' in field]
        with open(psc2_path, 'w') as psc2_file:
            psc2_file.write(header + '\n')
            for line in psytools_file:
                line = line.strip()
                items = line.split(',')
                psc1 = items[0]
                if 'id_check' in line:
                    # Psytools files contain identifying data,
                    # specifically lines containing items:
                    # * id_check_dob
                    # * id_check_gender
                    #
                    # As the name implies, the purpose of these items is
                    # cross-checking and error detection. They should not
                    # be used for scientific purposes.
                    #
                    # These items should therefore not be exposed to end
                    # users.
                    logging.debug('skipping line with "id_check" from {0}'
                                  .format(psc1))
                    continue
                # subject ID is PSC1 followed by '-C' or '-I'
                if '-' in psc1:
                    psc1, suffix = psc1.rsplit('-', 1)
                else:
                    suffix = None
                psc2 = None
                if psc1.startswith('TEST'):
                    logging.debug('skipping test subject {0}'
                                  .format(psc1))
                    continue
                elif psc1 in PSC2_FROM_PSC1:
                    logging.debug('converting subject {0} from PSC1 to PSC2'
                                  .format(psc1))
                    psc2 = PSC2_FROM_PSC1[psc1]
                    items[0] = '-'.join((psc2, suffix))
                else:
                    logging.error('PSC1 code missing from conversion table: {0}'
                                  .format(items[0]))
                    continue
                for i in convert:
                    if psc2 is None or psc2 not in DOB_FROM_PSC2:
                        items[i] = ''
                    else:
                        timestamp = datetime.strptime(items[i],
                                     '%Y-%m-%d %H:%M:%S.%f').date()
                        birth = DOB_FROM_PSC2[psc2]
                        age = timestamp - birth
                        items[i] = str(age.days)
                psc2_file.write(','.join(items) + '\n')


def create_psc2_files(psc1_dir, psc2_dir):
    """Anonymize and re-encode all psytools questionnaires within a directory.

    PSC1-encoded files are read from `master_dir`, anoymized and converted
    from PSC1 codes to PSC2, and the result is written in `psc2_dir`.

    Parameters
    ----------
    psc1_dir: str
        Input directory with PSC1-encoded questionnaires.
    psc2_dir: str
        Output directory with PSC2-encoded and anonymized questionnaires.

    """
    for psc1_file in os.listdir(psc1_dir):
        psc1_path = os.path.join(psc1_dir, psc1_file)
        psc2_path = os.path.join(psc2_dir, psc1_file)
        _create_psc2_file(psc1_path, psc2_path)


def main():
    create_psc2_files(PSYTOOLS_PSC1_DIR, PSYTOOLS_PSC2_DIR)


if __name__ == "__main__":
    main()
