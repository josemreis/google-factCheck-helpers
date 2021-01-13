#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan  9 22:44:13 2021

@author: jmr
"""

from requests.exceptions import HTTPError
import time
import requests
import json
from itertools import product
from datetime import datetime

class google_fct_wrapper:
    
    def __init__(self, json_query_path: str, **kwargs):
        """
        Instantiate class google fct pipeline
        args:
            api_key: str, google API key.
            q: str or list, textual query string or list of textual query strings, Required unless reviewPublisherSiteFilter is specified.
            languageCode : str or list, BCP-47 language code, e.g. "en-US" or "sr-Latn". Can be used to restrict results by language, though we do not currently consider the region. 
            reviewPublisherSiteFilter : str or list of strs, the review publisher site to filter results by, e.g. nytimes.com. 
            max_days_age : int, the maximum age of the returned search results, in days. Age is determined by either claim date or review date, whichever is newer. 
            pagination_size : int, the pagination size. We will return up to that many results. Defaults to 10 if not set. 
            pagination_token: str, the pagination token. 
            pagination_offset: int, an integer that specifies the current offset (that is, starting result location) in search results. This field is only considered if pageToken is unset. For example, 0 means to return results starting from the first matching result, and 10 means to return from the 11th result. 
        returns:
            instance of class google_fct_pipeline
        """
        ## read the query
        with open(json_query_path) as f:
            query = json.load(f)
        # query dict as attribute
        self.query_dict = query
        ## attrs: query
        for k in query.keys():
            setattr(self, k, query[k])
        ## attrs: additional
        for k in kwargs:
            setattr(self, k, kwargs[k])
        if self.key is None:
            raise ValueError('You must provide a google api key.')
        if self.query is None and self.reviewPublisherSiteFilter is None:
            raise ValueError('You must provide a query string or select a reviewer domain.')
    
    ### Make a get request to Google's claim search endpoint
    def claim_search(self, querystring : dict, verbose = True, max_retries = 30, back_off = 1.5):
        """ Wrapper to the claim search endpoint of googles FC tools API
        params:
            verbose: logical, defaults to True
            max_retries: int, how many times should we try the GET request
            back_off: float, exponential back off parameter
        returns:
            list of dictionaries
        see also:
            * endpoint docs: https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search
            * Getting a google api key: https://support.google.com/googleapi/answer/6158862?hl=en
            * BCP-47 language code directory: https://github.com/libyal/libfwnt/wiki/Language-Code-identifiers 
        """
        ### Prepare the get request
        ## define the endpoint
        endpoint = "https://content-factchecktools.googleapis.com/v1alpha1/claims:search"
        ### start the loop
        ### make the request 
        attempts = 0
        nxt = True
        response_list = []
        while nxt:
            while attempts < max_retries:
                attempts += 1
                sleep_time = round(attempts ** back_off, 1)
                try:
                    response = requests.get(url = endpoint, params = {k: v for k, v in querystring.items() if v is not None})
                    response.raise_for_status()
                    if verbose:
                        print(f'API Call to claim search endpoint. Status-code: {str(response.status_code)}\n')
                    break
                except HTTPError as http_err:
                    time.sleep(sleep_time)
                    print(f'HTTP error in API call occurred: {http_err}.\n - Retrying in {sleep_time} secs.')  
                except Exception as err:
                    raise ValueError(f'Another non HTTP Request error occurred: {err}.')
            ## parse response and append the output
            parsed_response = json.loads(response.text)
            if verbose:
                print(parsed_response['claims'])
            if len(parsed_response) > 0:
                for claim in parsed_response['claims']:    
                    response_list.append(parsed_response['claims'])
            ## more pages?
            if 'nextPageToken' not in parsed_response.keys():
                nxt = False
            else:
                ## assign the token for the next page to the query string
                querystring['pageToken'] = parsed_response['nextPageToken']
                if verbose:
                    print(f'\nFetching next page. Token: {parsed_response["nextPageToken"]}\n')
        ## return
        if len(response_list) > 0:
            out = response_list
        else:
            out = None
        return out
    
    def get_candidate_value(self, d: dict, key: str, candidate_expressions = list):
        """ Fetch the value given a key or one of a list of possible candidate keys or key[index] combos as expressions to be dynamically evaluated"""
        if d.get(key) is None:
            out = None
            for candidate in candidate_expressions:
                exp = f'd{candidate}'
                try:
                    result = eval(exp)
                    if result is not None and len(result) > 0:
                        out = result
                        break
                except:
                    pass
        else:
            out = d.get(key)
        return out
    
    def clean_up(self, response_list: list):
        """ Extract the relevant metadata """
        out = []
        for claim in response_list:
            ## normalize the dict
            for l in claim:
                cr = l['claimReview'][0]
                my_d = dict(claim_reviewed = l.get('text'),
                            claimant = l.get('claimant'),
                            claim_date = l.get('claimDate'),
                            fact_check_domain = self.get_candidate_value(cr, 'publisher_site', candidate_expressions = ['["publisher"]["site"]']),
                            fact_check_author_name = self.get_candidate_value(cr, 'publisher_name', candidate_expressions = ['["publisher"]["name"]', '["publisher"]["site"]']),
                            fact_check_title = cr.get('title'),
                            fact_check_language_code = cr.get('languageCode'))
                out.append(my_d)
        return out
        
    ### run the query
    def run_query(self, verbose = False):
        """ 
        Run multiple claim search calls.
        args:
            verbose: logical, print out the data as we collect it 
        returns:
            pandas df or json object
        """
        ### Generate batch queries
        ## if one of the dynamic parameters is not list, turn it to list
        q = (self.query if isinstance(self.query, list) else [self.query])
        languageCode = (self.languageCode if isinstance(self.languageCode, list) else [self.languageCode])
        reviewPublisherSiteFilter = (self.reviewPublisherSiteFilter if isinstance(self.reviewPublisherSiteFilter, list) else [self.reviewPublisherSiteFilter])
        ## find unique combinations of the parameters
        combinations = list(product(q,languageCode,reviewPublisherSiteFilter))
        ### Make the queries
        out = []
        query = dict(self.query_dict)
        for pars in combinations:
            ## add the dynamic parameters to the query string
            query['query'] = pars[0]
            query['languageCode'] = pars[1]
            query['reviewPublisherSiteFilter'] = pars[2]
            ## make the api cal
            resp = self.claim_search(querystring = query, verbose = verbose)
            ## make query dict with features to add
            pars_to_add = {k:v for k,v in query.items() if k not in ['key', 'pageToken', 'offset', 'pageSize']}
            pars_to_add['query_date'] = datetime.today().strftime('%Y-%m-%d')
            if resp is not None:
                print(resp)
                ## clean up
                cleaned = self.clean_up(response_list = resp)
                print(cleaned)
                out.append({"query_parameters" : {**pars_to_add}, "claim_search_results" : cleaned})
            else:
                print(f'No data retrieved for the query:\n{pars_to_add}\n')
        return out
    
if __name__ == "__main__":
    query_path = '/home/jmr/Desktop/example_query.json'
    api = google_fct_wrapper(json_query_path = query_path)
    test = api.run_query()
    for l in test:
        for d in l['claim_search_results']:
            print(f'{d["claim_reviewed"]}: {d["claimant"]};\nfrom: {d["fact_check_domain"]}\n')