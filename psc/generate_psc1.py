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

"""Generate codes to pseudonymize c-VEDA data.

The algorithm used here is certainly brain-dead. This is not reusable code
but is good enough for a one-shot run. I spent 10 minutes writing and it
took ~ 3 days to generate PSC1 codes for the c-VEDA projects.

Notes
-----
.. Damerau–Levenshtein distance
   https://en.wikipedia.org/wiki/Damerau%E2%80%93Levenshtein_distance

.. Lexicographic code
   https://en.wikipedia.org/wiki/Lexicographic_code

"""

from random import shuffle
from jellyfish import damerau_levenshtein_distance

DIGITS = 10
MAX_VALUE = 9999999
MIN_DISTANCE = 3


def largest_int_with_less_digits(n):
    """Returns the largets integer with less digits than the argument.

    Depending on the integer argument, it will typically return 9, 99,
    999, 9999, ...

    Parameters
    ----------
    n : int
        A positive integer.

    Returns
    -------
    int
        Largest positive integer with less digits than the argument,
        or None if no such integer exists.

    Examples
    --------

    >>> print(largest_int_with_less_digits(1234))
    999

    """
    length = len(str(n))
    if length > 1:
        n = 0
        for i in range(1, length):
            n = n * 10 + 9
        return n
    else:
        return None


def code_generator(digits, max_value, min_distance):
    """Generate distant enough numeric codes (Damerau-Levenshtein distance).

    Parameters
    ----------
    digits : int
        Number of digits the numeric code is made of. If needed the string
        will be padded with zeroes.

    max_value : int
        Maximal numeric value of the code.

    min_distance : int
        Minimal Damerau-Levenshtein distance between generated strings.

    Yields
    ------
    str
        A code is a string made of `digits` characters.

    """
    lexicode = []

    candidates = list(range(largest_int_with_less_digits(max_value) + 1,
                            max_value + 1))
    shuffle(candidates)

    for i in candidates:
        i = str(i)
        i = i.zfill(digits)
        if not lexicode or min(damerau_levenshtein_distance(i, j) for j in lexicode) >= min_distance:
            lexicode.append(i)
            yield i


def main():
    for code in code_generator(DIGITS, MAX_VALUE, MIN_DISTANCE):
        print(code)


if __name__ == '__main__':
    main()
