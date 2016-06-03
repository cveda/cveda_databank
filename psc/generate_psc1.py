#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Generate codes to pseudonymize c-VEDA data.

The algorithm used here is certainly brain-dead. This is not reusable code.
I spent 10 minutes writing and it took ~ 3 days to generate PSC1 codes for
the c-VEDA projects. This is good enough for a one-shot run.

Notes
-----
.. Damerau–Levenshtein distance
   https://en.wikipedia.org/wiki/Damerau%E2%80%93Levenshtein_distance

.. Lexicographic code
   https://en.wikipedia.org/wiki/Lexicographic_code

"""

from random import randrange, shuffle
from itertools import groupby
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
        if max(len(list(g)) for k, g in groupby(i)) > 2:  # avoid more than 2 consecutive identical characters
            continue
        i = i.zfill(digits)
        if not lexicode or min(damerau_levenshtein_distance(i, j) for j in lexicode) >= min_distance:
            lexicode.append(i)
            yield i


def main():
    for code in code_generator(DIGITS, MAX_VALUE, MIN_DISTANCE):
        print(code)


if __name__ == '__main__':
    main()
