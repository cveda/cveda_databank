#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2010-2019 CEA
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

"""Re-encode and anonymize Psytools files.

This script iterates over Psytools CSV files downloaded from the Delosis
server. For each file it will:
* substitute the PSC1 code for a PSC2 code,
* change acquisition dates into age in days at acquisition,
* remove some data (such as date of birth) used for cross-checking.

==========
Attributes
==========

Input
-----

PSYTOOLS_PSC1_DIR : str
    Source directory to read PSC1-encoded Psytools files from.

Output
------

PSYTOOLS_PSC2_DIR : str
    Target directory to write PSC2-encoded Psytools files to.

"""

PSC1_FROM_SAMPLE_ID = '/cveda/databank/framework/psc/omics/GSA_to_PSC1_IDs.csv'
SNPS_PSC1_DIR = '/cveda/databank/RAW/PSC1/omics/dna'
SNPS_PSC2_DIR = '/cveda/databank/RAW/PSC2/omics/dna'

import os
from csv import DictReader
import logging
logging.basicConfig(level=logging.ERROR)

# import ../cveda_databank
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
from cveda_databank import PSC2_FROM_PSC1


def _create_psc2_file(psc1_path, psc2_path, psc1_from_sample_id):
    """Pseudonymize a SNPs file.

    Parameters
    ----------
    psc1_path: str
        Input: PSC1-encoded SNPs file.
    psc2_path: str
        Output: PSC2-encoded SNPs file.

    """

    with open(psc1_path, 'r') as psc1_file, open(psc2_path, 'w') as psc2_file:
        # file header (from '[Header]' to '[Data]')
        for line in psc1_file:
            psc2_file.write(line)
            if line.startswith('[Data]'):
                break

        # column header
        line = next(psc1_file)
        snp_name, sample_id, line = line.split('\t', 2)
        assert(sample_id == 'Sample ID')
        line = snp_name + '\tPSC2\t' + line
        psc2_file.write(line)
    
        # de-identify actual data
        output = {}
        for line in psc1_file:
            snp_name, sample_id, line = line.split('\t', 2)
            psc1 = psc1_from_sample_id[sample_id]
            psc2 = PSC2_FROM_PSC1[psc1]
            line = snp_name + '\t' + psc2 + '\t' + line
            output.setdefault(psc2, []).append(line)
        for psc2 in sorted(output):
            for line in output[psc2]:
                psc2_file.write(line)


def _cleanup_snps_file_name(filename):
    STR_BATCH = '_Batch_'
    i1 = filename.find(STR_BATCH) + len(STR_BATCH)
    STR_FINALREPORT = '_FinalReport'
    i2 = filename.rfind(STR_FINALREPORT)
    batch = filename[i1:i2]

    if batch.startswith('1'):  # 1_1-96samples
        batch = '01'

    return filename[:i1] + batch + filename[i2:]


def create_psc2_files(psc1_dir, psc2_dir, psc1_from_sample_id):
    """Pseudonymize all SNPs files within a directory.

    PSC1-encoded files are read from `psc1_dir`, converted
    from PSC1 codes to PSC2, and the result is written in `psc2_dir`.

    Parameters
    ----------
    psc1_dir: str
        Input directory with PSC1-encoded SNPs files.
    psc2_dir: str
        Output directory with PSC2-encoded pseudonymized SNPs files.

    """
    for psc1_file in os.listdir(psc1_dir):
        if psc1_file.endswith('.txt'):
            psc1_path = os.path.join(psc1_dir, psc1_file)
            psc2_file = _cleanup_snps_file_name(psc1_file)
            psc2_path = os.path.join(psc2_dir, psc2_file)
            _create_psc2_file(psc1_path, psc2_path, psc1_from_sample_id)


def main():
    psc1_from_sample_id = {}
    with open(PSC1_FROM_SAMPLE_ID, 'r') as csvfile:
        reader = DictReader(csvfile)
        for row in reader:
            psc1_from_sample_id[row['GSA_ID']] = row['PSC1_ID']

    create_psc2_files(SNPS_PSC1_DIR, SNPS_PSC2_DIR, psc1_from_sample_id)


if __name__ == "__main__":
    main()
