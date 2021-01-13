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
PATH2DATASET2 = '/home/jmr/Desktop/FakeNews_meta.csv' # for the output

### define the relevant query parameters
#REV_DOMAIN = [
#        'checamos.afp.com', 
#        'piaui.folha.uol.com.br', 
#        'politica.estadao.com.br',
#        'aosfatos.org',
#        'noticias.uol.com.br',
#        'poligrafo.sapo.pt',
#        'observador.pt',
#        'factcheck.afp.com', 
#        'truthorfiction.com',
#        'fullfact.org',
#        'factual.afp.com',
#        'efe.com',
#        'newtral.es',
#        'faktencheck.afp.com',
#        'correctiv.org',
#        ]
REV_DOMAIN = None
Q = "covid"
API_KEY = open(PATH2KEY, 'r').readline().strip()
LANG_CODE = None
PAGESIZE = 10
MAXDAYS = 50
logger = "/home/jmr/Desktop/baaah.log"
### Pull the data
## instantiate class google
google_fn = google_fct_pipeline(api_key = API_KEY, q = Q, reviewer_domain_filter = REV_DOMAIN, lang_code = LANG_CODE, pagination_size = PAGESIZE, max_days_age = MAXDAYS, pagination_token = None, pagination_offset = None, log_path = logger)
## get google fct data
google_fct_data = google_fn.run_query(output_format = 'pandas', verbose = True)
print(google_fct_data)
google_fct_data.to_csv(PATH2DATASET2)
## Get the fake news metadata
fn_meta = google_fn.fetch_metadata(urls = google_fct_data['claimReview.url'].tolist(), output_format = 'pandas',log_path = logger)
fn_data = fn_meta.fn_data
### Merge and export
#out = fn_data.join(google_fct_data, on = 'claimReview.url', how = 'left')
fn_data.to_csv(PATH2DATASET)
## export fake news data as markdown table
#with open(PATH2DATASET2,'w') as outfile:
#    fn_data[["reviewRating.ratingValue", "reviewRating.bestRating", "reviewRating.worstRating", "itemReviewed.url", "itemReviewed.datePublished", "author.url", "author.sameAs"]].to_markdown(buf = "/home/jmr/Desktop/FakeNews_meta.md")


