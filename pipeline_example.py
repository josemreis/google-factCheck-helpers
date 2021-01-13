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
api = google_fct_wrapper(json_query_path = query_path)
google_data = api.run_query()
### fetch the fc urls
urls = []
for l in google_data:
    for d in l['claim_search_results']:
        print(f'Collecting metadata of {d["fact_check_url"]}')
        urls.append(d['fact_check_url'])
fc_urls = list(set(urls))
### parse claim review asynchronously
claim_review = async_claim_review_parser(urls = fc_urls)
to_export = []
for google_dict, cr_dict in zip(google_data, claim_review.cr_list):
    ## combine them
    if len(cr_dict) < 1:
        cr_dict = {}
    to_export.append({"claim_search_data" : {**google_dict}, "claim_review_metadata" : {**cr_dict}})
### export
with open('/home/jmr/Desktop/fakeNews_test_data.json', 'w') as f:
    json.dump(to_export, f, ensure_ascii=False, indent=4)
