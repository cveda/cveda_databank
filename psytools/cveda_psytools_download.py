#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2010-2017 CEA
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

"""Download Psytools data as compressed CSV files from the Delosis server.

Authentication tokens are read from file ~/.netrc.

==========
Attributes
==========

Output
------

PSYTOOLS_PSC1_DIR : str
    Target directory to write PSC1-encoded Psytools files to.

"""

import logging
logging.basicConfig(level=logging.ERROR)

import os
import requests
from io import BytesIO, TextIOWrapper
import gzip
import re

PSYTOOLS_PSC1_DIR = '/cveda/databank/RAW/PSC1/psytools'
BASE_URL = 'https://www.delosis.com/psytools-server/dataservice/dataset/'

TMT_DIGEST = 'TMT digest'
BASIC_DIGEST = 'Basic digest'

PSYTOOLS_DATASETS = (
    ('cVEDA_TMT', TMT_DIGEST),  # Trail making task
    ('cVEDA_TCI', BASIC_DIGEST),  # TCI
    ('cVEDA_MINI5', BASIC_DIGEST),  # M.I.N.I
    ('cVEDA_AAQ', BASIC_DIGEST),  # AAQ
    ('cVEDA_SCAMP_PARENT', BASIC_DIGEST),  # SCAMP PARENT questionnaire
    ('cVEDA_EATQr_SELF', BASIC_DIGEST),  # EATQr_SELF
    ('cVEDA_KIRBY', BASIC_DIGEST),  # Now or later?
    ('cVEDA_CORSI', BASIC_DIGEST),  # Corsi
    ('cVEDA_CBQ_PARENT', BASIC_DIGEST),  # CBQ
    ('cVEDA_SCAMP_SELF', BASIC_DIGEST),  # SCAMP SELF questionnaire
    ('cVEDA_ASSIST', BASIC_DIGEST),  # ASSIST
    ('cVEDA_PBI', BASIC_DIGEST),  # PBI
    ('cVEDA_MID', BASIC_DIGEST),  # MID
    ('cVEDA_SST', BASIC_DIGEST),  # SST
    ('cVEDA_BART', BASIC_DIGEST),  # BART
    ('cVEDA_EEQ', BASIC_DIGEST),  # Environmental Exposures Questionnaire
    ('cVEDA_APQ_CHILD', BASIC_DIGEST),  # APQ Child
    ('cVEDA_APQ_PARENT', BASIC_DIGEST),  # APQ Parent
    ('cVEDA_DS', BASIC_DIGEST),  # Digit Span
    ('cVEDA_SDQ_CHILD', BASIC_DIGEST),  # SDQ Child
    ('cVEDA_MPQ', BASIC_DIGEST),  # Medical Problems
    ('cVEDA_IFVCS', BASIC_DIGEST),  # IFVCS
    ('cVEDA_MINI5KID', BASIC_DIGEST),  # M.I.N.I KID
    ('cVEDA_ACEIQ', BASIC_DIGEST),  # ACEIQ
    ('cVEDA_SDIM', BASIC_DIGEST),  # SDI Migration
    ('cVEDA_SOCRATIS', BASIC_DIGEST),  # SOCRATIS
    ('cVEDA_PDS', BASIC_DIGEST),  # Physical Development
    ('cVEDA_PHIR', BASIC_DIGEST),  # PHI-R
    ('cVEDA_ANTHROPOMETRY', BASIC_DIGEST),  # ANTHROPOMETRY
    ('cVEDA_FHQ', BASIC_DIGEST),  # Family history
    ('cVEDA_SCQ', BASIC_DIGEST),  # School Climate Questionnaire
    ('cVEDA_SFQR', BASIC_DIGEST),  # Short Food Questionnaire- Revised
    ('cVEDA_ERT', BASIC_DIGEST),  # Emotion Recognition
    ('cVEDA_SDQ_PARENT', BASIC_DIGEST),  # SDQ Parent
    ('cVEDA_ASRSADHD', BASIC_DIGEST),  # ASRS - ADHD
    ('cVEDA_WCST', BASIC_DIGEST),  # Sort the cards
    ('cVEDA_TS', BASIC_DIGEST),  # Testing Situation
    ('cVEDA_BIG5', BASIC_DIGEST),  # BIG5
    ('cVEDA_DEBRIEF1', BASIC_DIGEST),  # Debrief
    ('cVEDA_DEBRIEF2', BASIC_DIGEST),  # Debrief
    ('cVEDA_DEBRIEF3', BASIC_DIGEST),  # Debrief
)

QUOTED_PATTERN = re.compile(r'".*?"', re.DOTALL)


def main():
    for task, digest in PSYTOOLS_DATASETS:
        digest = digest.upper().replace(' ', '_')
        dataset = 'cVEDA-{task}-{digest}.csv'.format(task=task, digest=digest)
        logging.info('downloading: %s', dataset)
        url = BASE_URL + dataset + '.gz'
        # connect to Delosis web service
        # let Requests module read authentication tokens from ~/.netrc
        r = requests.get(url)
        # read stream of CSV data sent by Delosis web service
        delosis_stream = BytesIO(r.content)
        # Delosis web service stopped compressing CSV data around 24 February 2017
        try:
            compressed_stream = gzip.GzipFile(fileobj=delosis_stream)
            uncompressed_stream = TextIOWrapper(compressed_stream,
                                                encoding='utf_8')
            uncompressed_data = uncompressed_stream.read()
            delosis_stream.close()
        except OSError:
            uncompressed_stream = TextIOWrapper(delosis_stream,
                                                encoding='utf_8')
            uncompressed_data = uncompressed_stream.read()
        # unfold quoted text spanning multiple lines
        data = QUOTED_PATTERN.sub(lambda x: x.group().replace('\n', '/'),
                                  uncompressed_data)
        # skip files that have not changed since last update
        psytools_path = os.path.join(PSYTOOLS_PSC1_DIR, dataset)
        if os.path.isfile(psytools_path):
            with open(psytools_path, 'r') as uncompressed_file:
                if uncompressed_file.read() == data:
                    logging.info('skip unchanged file: %s', psytools_path)
                    continue
        # write downloaded data into file
        with open(psytools_path, 'w') as uncompressed_file:
            logging.info('write file: %s', psytools_path)
            uncompressed_file.write(data)


if __name__ == "__main__":
    main()
