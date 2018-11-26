#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from cveda_databank import SEX_FROM_PSC1, PSC2_FROM_PSC1


def main():
    print(','.join(('PSC2', 'Sex')))
    for psc1 in SEX_FROM_PSC1:
        print(','.join((PSC2_FROM_PSC1[psc1], SEX_FROM_PSC1[psc1])))


if __name__ == "__main__":
    main()
