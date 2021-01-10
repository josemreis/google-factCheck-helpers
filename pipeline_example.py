#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  7 17:53:31 2021

@author: jmr
"""
from fake_news_pipeline import *
import pandas as pd

### Relevant paths
PATH2KEY = '/home/jmr/gfce_key.txt' # api key
PATH2DATASET = '/home/jmr/Desktop/FakeNews.csv' # for the output

### define the relevant query parameters
REV_DOMAIN = [
        'checamos.afp.com', 
        'piaui.folha.uol.com.br', 
        'factcheck.afp.com', 
        'truthorfiction.com', 
        'factual.afp.com/afp-espana', 
        'correctiv.org'
        ]
Q = None
API_KEY = open(PATH2KEY, 'r').readline().strip()
LANG_CODE = None
PAGESIZE = 10
MAXDAYS = 10

### Pull the data
## instantiate class google
google_pipeline = google_fct_pipeline(api_key = API_KEY, q = Q, reviewer_domain_filter = REV_DOMAIN, lang_code = LANG_CODE, pagination_size = PAGESIZE, max_days_age = MAXDAYS)
## get google fct data
google_fct_data = google_pipeline.run_query()
print(google_fct_data.info())
## Get the fake news metadata
fn_pipeline = fn_data_pipeline(urls = google_fct_data['claimReview.url'].tolist())
fn_data = fn_pipeline.fn_data
print(fn_data.info())

### Merge and export
#out = fn_data.join(google_fct_data, on = 'claimReview.url', how = 'left')
fn_data.to_csv(PATH2DATASET)



