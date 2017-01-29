#!/bin/sh

# download Psytools CSV files from Delosis server
/cveda/databank/framework/cveda_databank/psytools/cveda_psytools_download.py

# anonymize Psytools CSV files
if [ -r /tmp/psc2psc_2016-07-12.txt ]
then
    export PYTHONPATH=/cveda/databank/framework/cveda_databank
    /cveda/databank/framework/cveda_databank/psytools/cveda_psytools_anonymize.py
fi
