#!/bin/sh

# download Psytools CSV files from Delosis server
/cveda/databank/framework/cveda_databank/psytools/cveda_psytools_download.py 2>&1 | ts '\%Y-\%m-\%d \%H:\%M:\%S \%Z' >> /var/log/databank/cveda_psytools_download.log


# anonymize Psytools CSV files
if [ -r /tmp/psc2psc_2016-07-12.txt ]
then
    export PYTHONPATH=/cveda/databank/framework/cveda_databank
    /cveda/databank/framework/cveda_databank/psytools/cveda_psytools_anonymize.py 2>&1 | ts '\%Y-\%m-\%d \%H:\%M:\%S \%Z' >> /var/log/databank/cveda_psytools_anonymize.log
fi
