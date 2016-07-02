#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2010-2016 CEA
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

PSYTOOLS_PSC1_DIR = '/tmp'  #~ '/cveda/BL/raw/PSC1/psytools'
BASE_URL = 'https://psytools.delosis.com/psytools-server/dataservice/dataset/'
CA_BUNDLE = #~ '/cveda/delosisCA.pem'

import logging
logging.basicConfig(level=logging.INFO)

import os
import requests  # so much easier than most HTTP Python libraries!
from io import BytesIO, TextIOWrapper
import gzip
import re

BASIC_DIGEST = 'Basic digest'

CVEDA_PSYTOOLS_DATASETS = (
    ('IMGN_ESPAD_PARENT_RC5', BASIC_DIGEST),  # (Drug Use Questionnaire)
)

QUOTED_PATTERN = re.compile(r'".*?"', re.DOTALL)


def main():
    for task, digest in CVEDA_PSYTOOLS_DATASETS:
        digest = digest.upper().replace(' ', '_')
        dataset = 'IMAGEN-{task}-{digest}.csv'.format(task=task, digest=digest)
        logging.info('downloading: {0}'.format(dataset))
        url = BASE_URL + dataset + '.gz'
        # let Requests use ~/.netrc instead of passing an auth parameter
        #     auth = requests.auth.HTTPBasicAuth('...', '...')
        # no need to expose identifiers in the code!
        r = requests.get(url, verify=CA_BUNDLE)
        compressed_data = BytesIO(r.content)
        with gzip.GzipFile(fileobj=compressed_data) as uncompressed_data:
            # unfold quoted text spanning multiple lines
            uncompressed_data = TextIOWrapper(uncompressed_data)
            data = QUOTED_PATTERN.sub(lambda x: x.group().replace('\n', '/'),
                                      uncompressed_data.read())
            # skip files that have not changed since last update
            psytools_path = os.path.join(PSYTOOLS_PSC1_DIR, dataset)
            if os.path.isfile(psytools_path):
                with open(psytools_path, 'r') as uncompressed_file:
                    if uncompressed_file.read() == data:
                        logging.info('skip unchanged file: {0}'
                                     .format(psytools_path))
                        continue
            # write downloaded data into file
            with open(psytools_path, 'w') as uncompressed_file:
                logging.info('write file: {0}'.format(psytools_path))
                uncompressed_file.write(data)


if __name__ == "__main__":
    main()
