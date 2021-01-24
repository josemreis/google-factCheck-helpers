#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  7 17:53:31 2021

@author: jmr
"""
from google_fc_helpers.google_fc_wrapper import *
from google_fc_helpers.async_scraper import *
import json
from pathlib import Path
import os

### google fct call
## prep the query
PATH_TO_KEY = os.path.join(str(Path.home()), 'gfce_key.txt')
key = open(PATH_TO_KEY, 'r').readline().strip()
query = {
        "key": key,
        "query": ["covid", "Coronavirus"],
        "languageCode" : ['pt', 'es', 'en', 'de'],
        "reviewPublisherSiteFilter": None,
        "pageSize": 10,
        "maxAgeDays": 60
        }
# query = '/home/jmr/Desktop/example_query.json' # alternatively, feed it the query in json format
## make the call
cs = claim_search(query = query)
## run it
google_data = cs.run_query()
### fetch claim review metadata asynchronously
claim_review_data = async_claim_review_parser(claim_dict_list = google_data)
### export
### export
with open(Path(__file__).parent / "example_query.jsonfakeNews_test_data.json", 'w') as f:
    json.dump(claim_review_data.data, f, ensure_ascii=False, indent=4)
