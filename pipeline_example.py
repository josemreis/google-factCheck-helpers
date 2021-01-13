#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  7 17:53:31 2021

@author: jmr
"""
from claim_review_parser import *
from async_scraper import *
from google_fct_wrapper import * 
import json

### make an api call
query_path = '/home/jmr/Desktop/example_query.json'
api = google_fct_wrapper(query = query_path)
google_data = api.run_query()
### fetch claim review metadata asynchronously
claim_review_data = async_claim_review_parser(claim_dict_list = google_data)
### export
with open('/home/jmr/Desktop/fakeNews_test_data.json', 'w') as f:
    json.dump(claim_review_data.data, f, ensure_ascii=False, indent=4)
