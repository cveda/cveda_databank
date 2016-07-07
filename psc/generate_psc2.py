#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2016 CEA
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

"""Generate codes to pseudonymize c-VEDA data.

The algorithm used here is certainly brain-dead. This is not reusable code
but is good enough for a one-shot run. I spent 10 minutes writing and it
took ~ 3 days to generate PSC2 codes for the c-VEDA projects.

Notes
-----
.. Damerau–Levenshtein distance
   https://en.wikipedia.org/wiki/Damerau%E2%80%93Levenshtein_distance

.. Lexicographic code
   https://en.wikipedia.org/wiki/Lexicographic_code

"""

import sys
from random import shuffle
from jellyfish import damerau_levenshtein_distance

DIGITS = 10
MIN_DISTANCE = 3
PREFIX = '00'


def code_generator(lexicode, digits, prefix, min_distance):
    """Generate distant enough numeric codes (Damerau-Levenshtein distance).

    Parameters
    ----------
    lexicode : set
        Existing codes, new codes must be distant enough from existing codes.

    digits : int
        Number of digits the code is made of. If needed the string will be
        padded with zeroes.

    prefix : str
        First characters of the generated code, obviously their length must
        be less than `digits`.

    min_distance : int
        Minimal Damerau-Levenshtein distance between codes.

    Yields
    ------
    str
        A code is a string made of `digits` characters.

    """
    assert prefix.isdigit() and len(prefix) < digits
    lexicode = set(x[-digits:].zfill(digits)
                   for x in lexicode)
    digits -= len(prefix)
    candidates = set((prefix + str(x))
                     for x in range(10 ** (digits - 1), 10 ** digits))
    candidates -= lexicode
    shuffle(list(candidates))

    for i in candidates:
        if not lexicode or min(damerau_levenshtein_distance(i, j) for j in lexicode) >= min_distance:
            lexicode.add(i)
            yield i


def main():
    # read existing PSC1 codes or Imagen PSC2 codes
    existing = set()
    for line in sys.stdin:
        line = line.strip()
        existing.add(line)

    # take into account above codes when calculating distance between codes
    for code in code_generator(existing, DIGITS, PREFIX, MIN_DISTANCE):
        print('00' + code)


if __name__ == '__main__':
    main()
