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

import os
import zipfile
import zlib
import tempfile
from datetime import datetime
import shutil
import subprocess
from cveda_databank import PSC2_FROM_PSC1
import json
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


QUARANTINE_PATH = '/cveda/databank/RAW/QUARANTINE'
BIDS_PATH = '/cveda/databank/processed/nifti'
SKIP_PATH = '/cveda/databank/framework/meta_data/errors/mri_skip.json'


def quarantine_filename_semantics(filename):
    root, ext = os.path.splitext(filename)

    if (ext != '.zip'):
        logger.warn('%s: filename without ".zip" extension', filename)

    increment, suffix = root.split('_data_')
    increment = int(increment)

    psc1 = suffix[:-6]  # last 6 characters added by the upload portal
    if len(psc1) > 12:
        timepoint = psc1[12:]
        psc1 = psc1[:12]
    else:
        timepoint = 'BL'

    return increment, psc1, timepoint


def timestamps(top, include_dirs=True):
    min_timestamp = datetime.max
    max_timestamp = datetime.min

    for root, dirs, files in os.walk(top):
        if include_dirs:
            for dirname in dirs:
                path = os.path.join(root, dirname)
                timestamp = datetime.fromtimestamp(os.path.getmtime(path))
                min_timestamp = min(timestamp, min_timestamp)
                max_timestamp = max(timestamp, max_timestamp)
        for filename in files:
            path = os.path.join(root, filename)
            timestamp = datetime.fromtimestamp(os.path.getmtime(path))
            min_timestamp = min(timestamp, min_timestamp)
            max_timestamp = max(timestamp, max_timestamp)

    return (min_timestamp, max_timestamp)


def list_datasets(path):
    datasets = {}

    for zip_file in os.listdir(path):
        zip_path = os.path.join(path, zip_file)
        if not zipfile.is_zipfile(zip_path):
            logger.warn('%s: skip invalid ZIP file ', zip_file)
            continue

        # Unix timestamp of the ZIP file
        timestamp = os.path.getmtime(zip_path)

        # semantics of ZIP file name
        increment, psc1, timepoint = quarantine_filename_semantics(zip_file)

        # compare increment/timestamp of ZIP files, keep most recent
        timepoint = datasets.setdefault(timepoint, {})
        if psc1 in timepoint:
            old_zip_path, old_increment, old_timestamp = timepoint[psc1]
            if (increment <= old_increment or timestamp <= old_timestamp):
                if (increment >= old_increment or timestamp >= old_timestamp):
                    logger.error('%s: inconsistent timestamps', zip_file)
                continue
        timepoint[psc1] = (zip_path, increment, timestamp)

    return datasets


_BIDS_MAPPING = {
    'T1w': 'anat',
    'T2w': 'anat',
    'FLAIR': 'anat',
    'rest': 'func',
    'B0_map': 'fmap',
    'dwi': 'dwi',
    'dwi_rev': 'dwi',
    'dwi_ap': 'dwi',
}


def dcm2nii(src, dst, filename, comment):
    logger.info('%s: running dcm2niix: %s', src, dst)

    dcm2niix = ['dcm2niix',
                '-z', 'y', '-9'
                '-c', comment,
                '-o', dst,
                '-f', filename,
                src]
    completed = subprocess.run(dcm2niix,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    if completed.returncode:
        logger.error('%s: dcm2niix failed: %s',
                     src, completed.stdout)
        return completed.returncode

    return 0


_DWI_MAPPING = {
    'dwi': None,
    'dwi_rev': 'rev',
    'dwi_ap': 'ap',
}


def deidentify(timepoint, psc1, zip_path, bids_path):
    logger.info('%s/%s: deidentify', psc1, timepoint)

    psc2 = PSC2_FROM_PSC1[psc1]
    out_sub_path = os.path.join(bids_path, 'sub-' + psc2)
    out_ses_path = os.path.join(out_sub_path, 'ses-' + timepoint)

    # skip ZIP files that have already been processed
    if os.path.isdir(out_ses_path):
        zip_timestamp = datetime.fromtimestamp(os.path.getmtime(zip_path))
        min_timestamp, max_timestamp = timestamps(out_ses_path)
        if min_timestamp > zip_timestamp:
            return
        else:
            shutil.rmtree(out_ses_path)
            os.makedirs(out_ses_path)

    status = 0
    prefix = 'cveda-mri-' + psc1
    with tempfile.TemporaryDirectory(prefix=prefix) as tempdir:
        # unpack ZIP file into temporary directory
        zip_file = zipfile.ZipFile(zip_path)
        try:
            zip_file.extractall(tempdir)
        except (zipfile.BadZipFile, OSError, EOFError, zlib.error) as e:
            logger.error('%s/%s: corrupt ZIP file: %s',
                         psc1, timepoint,  str(e))
            return

        # process each sequence found in ZIP file
        for modality in os.listdir(tempdir):
            src = os.path.join(tempdir, modality)
            dst = os.path.join(out_ses_path, modality)

            # name files as suggested in BIDS
            if _BIDS_MAPPING[modality] == 'func':
                filename = ('sub-' + psc2 + '_ses-' + timepoint +
                            '_task-' + modality +
                            '_bold')
            elif _BIDS_MAPPING[modality] == 'fmap':
                filename = ('sub-' + psc2 + '_ses-' + timepoint)
            elif _BIDS_MAPPING[modality] == 'dwi':
                acq = _DWI_MAPPING[modality]
                if acq is None:
                    filename = ('sub-' + psc2 + '_ses-' + timepoint +
                                '_dwi')
                else:
                    filename = ('sub-' + psc2 + '_ses-' + timepoint +
                                '_acq-' + acq + '_dwi')
            else:
                filename = ('sub-' + psc2 + '_ses-' + timepoint +
                            '_' + modality)

            os.makedirs(dst)
            status = dcm2nii(src, dst, filename, psc2 + '/' + timepoint)
            if status:
                logger.error('%s/%s: cannot convert %s from DICOM to NIfTI: %d',
                             psc1, timepoint, modality, status)
                shutil.rmtree(dst)
                break

            # rename some files for BIDS compliance
            # remove useless extra files (such as ADC files)
            for f in os.listdir(dst):
                root, ext = os.path.splitext(f)
                if ext == '.gz':
                    root, ext = os.path.splitext(root)
                    ext += '.gz'
                if root.endswith('_c2'):  # MYSORE Philips Ingenia
                    root = root[:-len('_c2')]
                    os.rename(os.path.join(dst, f),
                              os.path.join(dst, root + ext))
                elif root.endswith('_dwi_ADC'):  # NIMHANS Siemens Skyra
                    logger.warning('%s/%s: DICOM conversion generates extra NIfTI file: %s',
                                   psc1, timepoint, f)
                    os.remove(os.path.join(dst, f))
                elif root.endswith('_e2_ph'):  # Siemens
                    root = root[:-len('_e2_ph')]
                    os.rename(os.path.join(dst, f),
                              os.path.join(dst, root + '_phasediff' + ext))
                elif root.endswith('_e1a'):  # PGIMER Philips Ingenia
                    root = root[:-len('_e1a')]
                    os.rename(os.path.join(dst, f),
                              os.path.join(dst, root + '_phasediff' + ext))
                elif root.endswith('_e1'):  # PGIMER Philips Ingenia
                    root = root[:-len('_e1')]
                    os.rename(os.path.join(dst, f),
                              os.path.join(dst, root + '_magnitude' + ext))
                else:
                    root = root.replace('sub-' + psc2 + '_ses-' +
                                        timepoint + '_', '')
                    EXPECTED = {
                        'T1w',
                        'T2w',
                        'FLAIR',
                        'task-rest_bold',
                        'dwi', 'acq-ap_dwi',
                        'acq-rev_dwi',
                        'phasediff', 'magnitude',
                    }
                    if root not in EXPECTED:
                        logger.error('%s/%s: unexpected BIDS file: %s',
                                     psc1, timepoint, f)
                        status = -1

    if status:
        shutil.rmtree(out_ses_path)
        if not os.listdir(out_sub_path):  # empty directory
            os.rmdir(out_sub_path)
    else:
        # rename some directories for BIDS compliance
        for modality in os.listdir(out_ses_path):
            src = os.path.join(out_ses_path, modality)
            dst = os.path.join(out_ses_path, _BIDS_MAPPING[modality])
            if src != dst:
                if os.path.isdir(dst):
                    for f in os.listdir(src):
                        os.rename(os.path.join(src, f),
                                  os.path.join(dst, f))
                    os.rmdir(src)
                else:
                    os.rename(src, dst)

    return status


def main():
    datasets = list_datasets(QUARANTINE_PATH)

    for timepoint, timepoint_datasets in datasets.items():
        for psc1, (zip_path, increment, timestamp) in timepoint_datasets.items():
            with open(SKIP_PATH) as skip_file:
                skip = json.load(skip_file)
                if timepoint in skip and psc1 in skip[timepoint]:
                    continue
            deidentify(timepoint, psc1, zip_path, BIDS_PATH)


if __name__ == "__main__":
    main()
