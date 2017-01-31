# -*- coding: utf-8 -*-
# noqa

# Copyright (c) 2014-2017 CEA
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

'''
Module `cveda_databank` provides shared functions and constants for databank
operations of the `c-VEDA project`_—mainly sanity checking of data uploaded
from acquisition centres.

.. _c-VEDA project: https://cveda.nimhans.ac.in

Constants
---------

.. py:data:: PSC2_FROM_PSC1

   This dictionary maps PSC1 codes to PSC2 codes.
   At module initialization, we read PSC1 keys and PSC2 values as 12-digit
   strings from file */cveda/databank/framework/psc/psc2psc_2016-07-12.txt*.

.. py:data:: PSC1_FROM_PSC2

   This dictionary maps PSC2 codes to PSC1 codes.
   At module initialization, we invert :py:data:`PSC2_FROM_PSC1` to build
   this dictionary.

.. py:data:: DOB_FROM_PSC1

   This dictionary maps PSC1 codes to the date of birth of the relevant subject.
   At module initialization, we read date of birth from Psytools questionnaires
   ACE-IQ and PHIR. We discard subjects with inconsistent data.

.. py:data:: SEX_FROM_PSC1

   This dictionary maps PSC1 codes to the sex of the relevant subject.
   At module initialization, we read sex from Psytools questionnaires ACE-IQ,
   PDS and SDIM. We discard subjects with inconsistent data.

Constants
---------

Classes
-------

.. autoexception:: Error
   :members:
   :undoc-members:
   :show-inheritance:

'''
from .core import PSC2_FROM_PSC1, PSC1_FROM_PSC2
from .core import DOB_FROM_PSC1, SEX_FROM_PSC1
from .core import Error
from .psytools import read_psytools
from .dicom_utils import read_metadata
from .image_data import walk_image_data, report_image_data

from . import sanity
