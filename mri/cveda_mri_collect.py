#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
from datetime import date
from cveda_databank.sanity import check_zip_name
from cveda_databank.sanity import check_zip_content
from cveda_databank import PSC2_FROM_PSC1
from cveda_databank import Error


UPLOAD_PATH = '/cveda/chroot/upload'
QUARANTINE_PATH = '/cveda/chroot/quarantine'
TRASH_NAME = '.trash'
ERROR_SUFFIX = '.error.txt'


def check_zip(path):
    psc1, errors = check_zip_name(path)
    if psc1 in PSC2_FROM_PSC1:
        expected = {
            'T1w': 'Good',
            'rest': 'Good',
            'B0_map': 'Good',
            'dwi_rev': 'Good',
            'dwi': 'Good',
            'FLAIR': 'Good',
            'T2w': 'Good',
        }
        dummy_psc1, errors2 = check_zip_content(path, psc1,
                                                date=None, expected=expected)
        errors.extend(errors2)
    else:
        errors.append(Error(path, 'Unknown PSC1 code in file name: {0}'
                                   .format(psc1)))
    return psc1, errors


def trash(path):
    if os.path.lexists(path):
        # create today's trash folder
        today = date.today()
        today_path = os.path.join(os.path.dirname(path), TRASH_NAME, str(today))
        if not os.path.isdir(today_path):
            os.makedirs(today_path, mode=0o750)  # exception should "never happen"
        # if needed create a unique file name in the trash
        target_path = os.path.join(today_path, os.path.basename(path))
        index = 0
        while os.path.lexists(target_path):
            index += 1
            target_path = os.path.join(today_path,
                                       os.path.basename(path) + '.' + str(index))
        # move file to trash
        os.rename(path, target_path)


def quarantine(path, quarantine):
    # if file already exists in quarantine, trash old file
    if os.path.lexists(path):
        target_path = os.path.join(quarantine, os.path.basename(path))
        if os.path.lexists(target_path):
            trash(target_path)
        os.rename(path, target_path)


def process_upload(path):
    # iterate over centers
    for center in os.listdir(path):
        center_path = os.path.join(path, center)
        if os.path.isdir(center_path):
            # iterate over ZIP files in each center
            for entry in os.listdir(center_path):
                if entry == TRASH_NAME or entry.endswith(ERROR_SUFFIX):
                    continue
                entry_path = os.path.join(center_path, entry)
                if os.path.isfile(entry_path) and not os.path.islink(entry_path):
                    # check each ZIP file
                    dummy_psc1, errors = check_zip(entry_path)
                    # reset log
                    log_path = entry_path + ERROR_SUFFIX
                    trash(log_path)
                    if errors:
                        # log error
                        with open(log_path, 'w', newline='\r\n') as log:
                            for e in errors:
                                print('{0}: {1}'.format(e.path, e.message),
                                      file=log)
                        # move to trash
                        trash(entry_path)
                    else:
                        quarantine_path = os.path.join(QUARANTINE_PATH, center)
                        if os.path.isdir(quarantine_path):
                            # move to quarantine
                            quarantine(entry_path, quarantine_path)
                        else:
                            print('Missing center "{0}" in quarantine: {1}'
                                  .format(center, QUARANTINE_PATH),
                                  file=sys.stderr)
                else:
                    print('Unexpected entry "{0}" in center folder: {1}'
                          .format(entry, center_path), file=sys.stderr)
        else:
            print('Unexpected file "{0}" in upload folder: {1}'
                  .format(center, path), file=sys.stderr)


def main():
    process_upload(UPLOAD_PATH)


if __name__ == '__main__':
    main()
