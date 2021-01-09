#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  7 17:53:31 2021

@author: jmr
"""
from claim_search import *

## path to the txt file with google's API key
PATH2KEY = '/home/jmr/gfce_key.txt' 

### define the relevant query parameters
Q = 'Antifa'
API_KEY = open(PATH2KEY, 'r').readline()
LANG_CODE = None
PAGESIZE = 100
MAXDAYS = 1
OUT = "pandas"
### make the query
out = google_claim_search(api_key = API_KEY, q = Q, lang_code = LANG_CODE, pagination_size = PAGESIZE, max_days_age = MAXDAYS, output_format = OUT)
print(out)
for claim in out:
    try:
        claimant = claim['claimant']
        the_claim = claim['text']
        fc = claim['claimReview.url']
        try:
            fn = claim['itemReviewed.url']
        except:
            if 'itemReviewed.author.sameAs' in claim.keys() and 'http' in claim['itemReviewed.author.sameAs']:
                fn = claim['itemReviewed.author.sameAs']
            else:
                fn = 'No source found'
        print(f'{claimant}: "{the_claim}";\nfc source: {fc};\nFN source: {fn}.\n\n')
    except:
        pass