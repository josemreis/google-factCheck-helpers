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
                    if verbose:
                        print(f'Making query to claim search endpoint\nq:{q}\nmax_days_age:{self.max_days_age}\nreviewer_domain_filter:{reviewer_domain_filter}\n')
                    response = requests.get(url = endpoint, params = {k: v for k, v in querystring.items() if v is not None})
                    response.raise_for_status()
                    if verbose:
                        print(f'API Call to claim search endpoint. Status-code: {str(response.status_code)}\n')
                    break
                except HTTPError as http_err:
                    time.sleep(sleep_time)
                    print(f'HTTP error occurred: {http_err}.\n - Retrying in {sleep_time} secs.')  
                except Exception as err:
                    raise ValueError(f'Another non HTTP Request error occurred: {err}.')
            ## parse response and append the output
            parsed_response = json.loads(response.text)
            if verbose:
                print(parsed_response)
            if len(parsed_response) > 0:
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
            print(f'No data retrieved for the query:\nq:{q}\nmax_days_age:{self.max_days_age}\nreviewer_domain_filter:{reviewer_domain_filter}\n')
        return out
    
    ### parse claim search
    def parse_claim_search(self, response_list = None, query_dict = None):
        """flatten claim search dict and add query parameters as features"""
        out = []
        for claim in response_list:
            ## normalize the dict
            for l in claim:
                flat = self.flatten_json({(k) : (v[0] if isinstance(v, list) else v) for k,v in l.items()})
                ## change text var and assign query variables    
                new_d = {}
                for k, v in flat.items():
                    if k == 'text':
                        new_d['claim'] = v
                    else:
                        new_d[k] = v
                ## add query features
                new_d2 = {**query_dict, **new_d}
                ## assign to the respons level list
                out.append(new_d2)
        return out
        
    ### run the query
    def run_query(self, verbose = False, output_format = 'json'):
        """ 
        Run multiple claim search calls.
        args:
            verbose: logical, print out the data as we collect it 
            output_format: str, ["pandas", "json"]
        returns:
            pandas df or json object
        """
        ### Generate batch queries
        ## if one of the dynamic parameters is not list, turn it to list
        q = (self.q if isinstance(self.q, list) else [self.q])
        lang_code = (self.lang_code if isinstance(self.lang_code, list) else [self.lang_code])
        reviewer_domain_filter = (self.reviewer_domain_filter if isinstance(self.reviewer_domain_filter, list) else [self.reviewer_domain_filter])
        ## find unique combinations of the parameters
        combinations = list(product(q,lang_code,reviewer_domain_filter))
        ### Make the queries
        out = []
        for pars in combinations:
            resp = self.claim_search(q = pars[0], lang_code = pars[1], reviewer_domain_filter = pars[2], verbose = verbose)
            if resp is not None:
                ## make query dict with features to add
                pars_to_add = {
                        'query_keyword': pars[0], 
                        'query_lang_code': pars[1], 
                        'query_reviewer_domain': pars[2], 
                        'query_max_day_range' : self.max_days_age
                        }
                ## parse the response
                parsed = self.parse_claim_search(response_list = resp, query_dict = pars_to_add)
                out.append(parsed)
        ## transform to the selected output format
        if output_format not in ['pandas', 'json']:
            raise ValueError('Output format must be either "json" or "pandas" for a pandas df.')
        else:
            # nested list of dicts to pandas
            df_list = []
            for l in out:
                as_pandas = pd.concat([pd.DataFrame([d]) for d in l], ignore_index = True)
                df_list.append(as_pandas)
            df = pd.concat(df_list).drop_duplicates(subset = 'claimReview.url').reset_index(drop=True)
            if output_format == 'json':
                # back to json
                out = df.to_json()
            else:
                # as is
                out = df
        return out
 
    ### flatten a nested dictionary
    def flatten_json(self, y, sep = "."):
        """ flatten a nested dictionary, source: https://towardsdatascience.com/flattening-json-objects-in-python-f5343c794b10"""
        out = {}
        def flatten(x, name='', sep = sep):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + sep)
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + sep)
                    i += 1
            else:
                out[name[:-1]] = x
        flatten(y)
        return out
    
    class fetch_metadata:
        
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
        def __init__(self, urls, output_format):
            """ 
            Instantiate class fetch_metadata. 
            args:
                urls: list, list of urls
                output_format: str, ["pandas", "json"]
            returns:
                pandas df or json object
            """
            self.urls = urls
            self.output_format = output_format
            # Global Place To Store The Data:
            self.all_data  = []
            self.fn_data = None
            ### run the async scraper
            return asyncio.run(self.claim_review_async())
    
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
            response = await s.get(url)
            try:
                claim_review_script = response.html.xpath('//script[@type="application/ld+json"]/text()')
                if len(claim_review_script) < 1:
                    raise ValueError(f'Error retrieving the claimReview json from page({url}).')
                ## parse the metadata into json and remove ws
                claim_review_data = json.loads(claim_review_script[0].replace("\n", ""))    
                print(claim_review_data)
                return claim_review_data
            except Exception as e:
                print(f'Error at {url}: {str(e)}')
        
        async def claim_review_async(self):
            """ Run the scrapers asynchronously and clean up the data"""
            ## start an asyncronous session
            s = AsyncHTMLSession()
            ## define the tasks
            tasks = []
            for url in self.urls:
                tasks.append(self.async_cr_task(s = s, url = url))
            ## fetch the data async
            raw = await asyncio.gather(*tasks)
            # assign the raw data
            self.all_data.extend(raw)
            ## clean up
            out = []
            for d, url in zip(raw, self.urls):
                if d is not None:
                    ## normalize. claimReview data is an attribute of the '@graph' list
                    if isinstance(d, list):
                        d = d[0] 
                    if '@graph' in d.keys():
                        d = d['@graph']
                        flat_list = [google_fct_pipeline.flatten_json(self, x) for x in d]    
                        rel_dict = [d2 for d2 in flat_list if 'claimReviewed' in d2.keys() or 'claimReviewed' in d2.keys()]
                    else:
                        ## only the features of @graph are included in the dict. Goes as is
                        flat_list = [google_fct_pipeline.flatten_json(self, d)]
                        rel_dict = [d2 for d2 in flat_list if 'claimReviewed' in d2.keys() or 'claimReviewed' in d2.keys()]
                    if len(rel_dict) > 0:
                        print(rel_dict[0])
                        out.append(rel_dict[0])
            ## transform the output
            if self.output_format not in ['pandas', 'json']:
                raise ValueError('Output format must be either "json" or "pandas" for a pandas df.')
            else:
                if self.output_format == 'json':
                    out = json.dumps(out)
                else:
                    out = pd.DataFrame(out)
            self.fn_data = out
                
      
        
    
    
