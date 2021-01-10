#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan  9 22:44:13 2021

@author: jmr
"""
from requests.exceptions import HTTPError
import time
from requests_html import AsyncHTMLSession
import requests
import json
import pandas as pd
import asyncio
from itertools import product

class google_fct_pipeline:
    def __init__(self, api_key = None, q = None, lang_code = None, reviewer_domain_filter = None, max_days_age = None, pagination_size = 100, pagination_token = None, pagination_offset = None):
        """
        Instantiate class google fct pipeline
        args:
            api_key: str, google API key.
            q: str or list, textual query string or list of textual query strings, Required unless reviewer_domain_filter is specified.
            lang_code : str or list, BCP-47 language code, e.g. "en-US" or "sr-Latn". Can be used to restrict results by language, though we do not currently consider the region. 
            reviewer_domain_filter : str or list of strs, the review publisher site to filter results by, e.g. nytimes.com. 
            max_days_age : int, the maximum age of the returned search results, in days. Age is determined by either claim date or review date, whichever is newer. 
            pagination_size : int, the pagination size. We will return up to that many results. Defaults to 10 if not set. 
            pagination_token: str, the pagination token. 
            pagination_offset: int, an integer that specifies the current offset (that is, starting result location) in search results. This field is only considered if pageToken is unset. For example, 0 means to return results starting from the first matching result, and 10 means to return from the 11th result. 
        returns:
            instance of class google_fct_pipeline
        """
        if api_key is None:
            raise ValueError('You must provide a google api key.')
        else:
            self.api_key = api_key
        if q is None and reviewer_domain_filter is None:
            raise ValueError('You must provide a query string or select a reviewer domain.')
        self.q = q
        self.reviewer_domain_filter = reviewer_domain_filter
        self.lang_code = lang_code
        self.max_days_age = max_days_age
        self.pagination_size = pagination_size
        self.pagination_token = pagination_token 
        self.pagination_offset = pagination_offset
        
    ### Make a get request to Google's claim search endpoint
    def claim_search(self, q = None, lang_code = None, reviewer_domain_filter = None, verbose = True, max_retries = 30, back_off = 1.5):
        """ Wrapper to the claim search endpoint of googles FC tools API
        
        params:
            q: str or list, textual query string or list of textual query strings, Required unless reviewer_domain_filter is specified.
            lang_code : str or list, BCP-47 language code, e.g. "en-US" or "sr-Latn". Can be used to restrict results by language, though we do not currently consider the region. 
            reviewer_domain_filter : str or list of strs, the review publisher site to filter results by, e.g. nytimes.com. 
            verbose: logical, defaults to True
            max_retries: int, how many times should we try the GET request
            back_off: float, exponential back off parameter
            
        returns:
            pandas data frame
        see also:
            * endpoint docs: https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search
            * Getting a google api key: https://support.google.com/googleapi/answer/6158862?hl=en
            * BCP-47 language code directory: https://github.com/libyal/libfwnt/wiki/Language-Code-identifiers 
        """
        ### Prepare the get request
        ## define the endpoint
        endpoint = "https://content-factchecktools.googleapis.com/v1alpha1/claims:search"
        ### start the loop
        ## define the query string. q, lang_code, and reviewer_domain_filter are allowed dynamic, the remaining are static and define at the moment of class instatiation.
        querystring = {
                'key': self.api_key,
                'query' : q,
                'languageCode' : lang_code,
                'reviewPublisherSiteFilter' : reviewer_domain_filter,
                'maxAgeDays' : self.max_days_age,
                'pageSize' : self.pagination_size,
                'pageToken' : self.pagination_token,
                'offset' : self.pagination_offset
                }
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
                    break
                except HTTPError as http_err:
                    time.sleep(sleep_time)
                    print(f'HTTP error occurred: {http_err}.\n - Retrying in {sleep_time} secs.')  
                except Exception as err:
                    raise ValueError(f'Another non HTTP Request error occurred: {err}.')
            ## parse response and append the output
            parsed_response = json.loads(response.text)
            if len(parsed_response) > 0:
                ## normalize the dict and turn to pandas df
                resp_cont = []
                for l in parsed_response['claims']:
                    resp_cont.append(pd.json_normalize({(k) : (v[0] if isinstance(v, list) else v) for k,v in l.items()}, sep = "."))
                resp_df = pd.concat(resp_cont)
                response_list.append(resp_df)
                if verbose:
                    print(parsed_response['claims'][0])
            if 'nextPageToken' not in parsed_response.keys():
                nxt = False
            else:
                ## assign the token for the next page to the query string
                querystring['pageToken'] = parsed_response['nextPageToken']
            ## put all into one df
            if len(response_list) > 0:
                out = pd.concat(response_list)
                ## add query parameters
                out['query_keyword'] = q
                out['query_days_range'] = self.max_days_age
                out['query_reviewer_domain'] = reviewer_domain_filter
                out['query_lang_code'] = lang_code
            else:
                out = None
                print(f'No data retrieved for the query:\n{querystring}')
        return out
    
    ### run the query
    def run_query(self):
        """ Run multiple claim search calls."""
        ### Generate batch queries
        ## if one of the dynamic parameters is not list, turn it to list
        q = (self.q if isinstance(self.q, list) else [self.q])
        lang_code = (self.lang_code if isinstance(self.lang_code, list) else [self.lang_code])
        reviewer_domain_filter = (self.reviewer_domain_filter if isinstance(self.reviewer_domain_filter, list) else [self.reviewer_domain_filter])
        ## find unique combinations of the parameters
        combinations = list(product(q,lang_code,reviewer_domain_filter))
        ### Make the queries
        df_list = []
        for pars in combinations:
            resp = self.claim_search(q = pars[0], lang_code = pars[1], reviewer_domain_filter = pars[2])
            if resp is not None:
                df_list.append(resp)
        return pd.concat(df_list)
    
class fn_data_pipeline:
    
    """
    Scraper of the claimReview json script in fact check urls since Google fact check 
    explorer claim search endpoint does not return the complete claimReview json.
    
    Example of full claimReview json schema:
                    '
                        {
                    "@context": "https://schema.org",
                    "@graph": [
                        {
                            "itemReviewed": {
                                "@type": "CreativeWork",
                                "url": "https://blog.naver.com/akwptmxl/222190223317",
                                "datePublished": "2020-12-30",
                                "author": {
                                    "@type": "Organization",
                                    "name": "multiple sources"
                                }
                            },
                            "author": {
                                "@type": "Organization",
                                "@id": "https://factcheck.afp.com/",
                                "name": "Fact Check",
                                "url": "https://factcheck.afp.com/",
                                "sameAs": "https://twitter.com/AFPFactCheck",
                                "logo": {
                                    "@type": "ImageObject",
                                    "url": "https://factuel.afp.com/sites/all/themes/custom/afpblog/v2/assets/img/Logo_AFP.svg",
                                    "width": "",
                                    "height": ""
                                }
                            },
                            "reviewRating": {
                                "@type": "Rating",
                                "ratingValue": "1",
                                "bestRating": "5",
                                "worstRating": "1",
                                "alternateName": "FALSE"
                            },
                            "claimReviewed": "Whipped cream was banned in South Korean cafes in January 2021",
                            "@type": "ClaimReview",
                            "name": "Korean social media posts falsely claim that whipped cream was banned in South Korean cafes in January 2021",
                            "datePublished": "2021-01-05 05:00",
                            "url": "https://factcheck.afp.com/korean-social-media-posts-falsely-claim-whipped-cream-was-banned-south-korean-cafes-january-2021"
                        }
                    ]
                }'
    """
    
    ### Fetch claim review data straight from the source urls
    def __init__(self, urls):
        self.urls = urls
        # Global Place To Store The Data:
        self.all_data  = []
        self.fn_data = None
        ### run the async scraper
        asyncio.run(self.claim_review_async())

    ### Retrieving the missing claimReview data from the FC websites
    ## asynchronous get requests for fetching the claimReviews from the websites
    async def async_cr_task(self, s, url):
        """
        Visits a fact check, looks for a script containing claimReview metadata (https://schema.org/ClaimReview). 
        If present, it parses it and returns a list with the retrieved metadata as dict. Else, it throws an error.
        args:
            page: str, Fact check page
        returns:
            claimReview json
        
        """
        r = await s.get(url)
        try:
            claim_review_script = r.html.xpath("//script[contains(., 'claimReviewed')]/text()")
            if len(claim_review_script) < 1:
                raise ValueError(f'Error retrieving the claimReview json from page({url}).')
            ## parse the metadata into json and remove ws
            claim_review_data = json.loads(claim_review_script[0].replace("\n", ""))    
            print(claim_review_data)
            return claim_review_data
        except Exception as e:
            print(f'Error at {url}: {str(e)}')
    
    async def claim_review_async(self):
        ## start an asyncronous session
        s = AsyncHTMLSession()
        ## define the tasks
        tasks = []
        for url in self.urls:
            tasks.append(self.async_cr_task(s = s, url = url))
        ## start the loop
        raw = await asyncio.gather(*tasks)
        # assing
        self.all_data.extend(raw)
        ## clean up
        out = []
        for d, url in zip(raw, self.urls):
            if d is not None:
                ## flatten
                if isinstance(d, list):
                    d = d[0]
                if '@graph' in d.keys():
                    d = d['@graph'][0]
                ## normalize
                normalized = pd.json_normalize({(k) : (v[0] if isinstance(v, list) else v) for k,v in d.items()}, sep = ".")
                filtered = normalized.filter(regex = "itemReviewed|reviewRating", axis = 1)
                as_dict = filtered.to_dict(orient = 'records')[0]
                as_dict['claimReview.url'] = url
                out.append(as_dict)
        df = pd.DataFrame(out)
        self.fn_data = df
        return df   
            
  
    


