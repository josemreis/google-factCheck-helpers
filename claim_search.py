#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 12:33:46 2020

@author: jmr
"""
import requests
from requests.exceptions import HTTPError
import time
import requests_html
import json
import pandas as pd
import waybackpy

### get request with expontential back_off
def get_request_backoff(url = None, query_string = None, max_retries = 50, back_off = 1.5, session = None):
    """
    GET request with exponential back-off
        _______PARAMS_______
        url: str
        query_string: see below
        max_retries: int, how many times should we try the GET request
        back_off: float, exponential back off parameter
    """
    ## GET request with exponential back-off
    attempts = 0
    while attempts < max_retries:
        attempts += 1
        sleep_time = round(attempts ** back_off, 1)
        try:
            if session != None:
                response = session.get(url)
            else:
                response = requests.request("GET", url, params=query_string)
            response.raise_for_status()
        except HTTPError as http_err:
            time.sleep(sleep_time)
            print(f'HTTP error occurred: {http_err}.\n - Retrying in {sleep_time} secs.')  
        except Exception as err:
            time.sleep(sleep_time)
            print(f'Another non HTTP Request error occurred: {err}. \n - Retrying in {sleep_time} secs.')
    return response 

### Flatten the claimReview dictionary
def flatten(d, sep='.', filter_regex = "itemReviewed|reviewRating"):
    """
    Flatten and filter keys from a claimReview dictionary (https://schema.org/ClaimReview).
    
        _______PARAMS_______
        d : dict
        sep : str, string separating the concatenated keys
        filter_regex: str, regular expression for filtering relevant keys
    """
    ## flatten
    if '@graph' in d.keys():
        d = d['@graph']
    if isinstance(d, list):
        d = d[0]
    normalized = pd.json_normalize({(k) : (v[0] if isinstance(v, list) else v) for k,v in d.items()}, sep = sep)
    ## filter
    if isinstance(filter_regex, str):
        normalized = normalized.filter(regex = filter_regex, axis = 1)
    return normalized.to_dict(orient = 'records')[0]

### Pull full claim review json from a FC page
def get_claimReview_meta(page = None, html_session = None):
    """
        Visits a fact check, looks for a script containing claimReview metadata (https://schema.org/ClaimReview). 
        If present, it parses it and returns a list with the retrieved metadata as dict. Else, it throws an error.
    
        _______PARAMS_______
        page: str, Fact check page
        html_session: HTMLSession object from the requests-html module
        see also:
            * Example of claimReview json schema:
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
    ### make the request and parse the page
    if html_session == None:
        html_session = requests_html.HTMLSession()
    r = get_request_backoff(page, session = html_session)
    if not r.ok:
        ### retrieve the oldest archived version of the page using IAs wayback machine
        wayback = waybackpy.Url(page) 
        try:
            old_archive = wayback.oldest().archive_url
        except:
            raise ValueError (f'The requested page ({page}) cannot be reached and there is no archive of it.')
        ## re-try
        r = session.get(old_archive)
        if not r.ok:    
            raise ValueError (f'The requested page ({page}) cannot be reached and there is no archive of it.')    
    ### identify and parse the js script containing the claimReview schema
    claim_review_script = r.html.xpath("//script[contains(., 'claimReviewed')]/text()")
    if len(claim_review_script) < 1:
        raise ValueError(f"Couldn't find the script claimReview metadata for page: {page}.\n Double-check that it exists.")
    ## parse the metadata into json and remove ws
    claim_review_data = json.loads(claim_review_script[0].replace("\n", ""))
    ### parse the relevant data
    relevant_meta = []
    if isinstance(claim_review_data, dict):
        try:
            flattened = flatten(claim_review_data)
            if len(flattened) > 0:
                relevant_meta.append(flattened)
        except:
            pass
    else:
        ## if it comes in several different lists containing dictionaries
        for i in claim_review_data:
            try:
                ## different websites have different depths in their dicts - flatten the keys
                flattened = flatten(i)
                if len(flattened) > 0:
                    relevant_meta.append(flattened)
            except:
                pass
    return relevant_meta

### google api claim search wrapper
def google_claim_search(api_key = None, q = None, lang_code = None, reviewer_domain_filter = None, max_days_age = None, pagination_size = 100, pagination_token = None, pagination_offset = None, verbose = True):
    """
    Wrapper to the claim search endpoint of googles FC tools API
    
        _______PARAMS_______
        api_key: str, google API key.
        q: str, textual query string, Required unless reviewer_domain_filter is specified.
        lang_code : str, BCP-47 language code, e.g. "en-US" or "sr-Latn". Can be used to restrict results by language, though we do not currently consider the region. 
        reviewer_domain_filter : str, the review publisher site to filter results by, e.g. nytimes.com. 
        max_days_age : int, the maximum age of the returned search results, in days. Age is determined by either claim date or review date, whichever is newer. 
        pagination_size : int, the pagination size. We will return up to that many results. Defaults to 10 if not set. 
        pagination_token: str, the pagination token. 
        pagination_offset: int, an integer that specifies the current offset (that is, starting result location) in search results. This field is only considered if pageToken is unset. For example, 0 means to return results starting from the first matching result, and 10 means to return from the 11th result. 
    
    see also:
        * endpoint docs: https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search
        * Getting a google api key: https://support.google.com/googleapi/answer/6158862?hl=en
        * BCP-47 language code directory: https://github.com/libyal/libfwnt/wiki/Language-Code-identifiers 
    """
    ### Prepare the get request
    ## define the endpoint
    endpoint = "https://content-factchecktools.googleapis.com/v1alpha1/claims:search"
    ## define the remaining headers of the request
    querystring = {
            'key': api_key,
            'query' : q,
            'languageCode' : lang_code,
            'reviewPublisherSiteFilter' : reviewer_domain_filter,
            'maxAgeDays' : max_days_age,
            'pageSize' : pagination_size,
            'pageToken' : pagination_token,
            'offset' : pagination_offset
            }
    if not isinstance(querystring['key'], str):
        raise ValueError('You must provide a google api key.')
    elif not isinstance(querystring['query'], str) and not isinstance(querystring['reviewer_domain_filter'], str):
        raise ValueError('You must provide a query string or select a reviewer domain.')
    else:
        ## remove undefined params from the dict
        clean_qs = {k: v for k, v in querystring.items() if v is not None}
        ### make the first request
        response = get_request_backoff(url = endpoint, query_string = clean_qs, max_retries = 30, back_off = 1.5)
        ## parse
        parsed_response = json.loads(response.text)
        if verbose:
                print(parsed_response)
        ## deal with possible pagination. Loop across the different results until there is no next page token
        response_list = [parsed_response]
        try:
            nxt = parsed_response['nextPageToken']
        except:
            nxt = None
        # Start the while loop
        while nxt != None:
            ## prep the new query string
            clean_qs['pageToken'] = nxt
            ## new request
            response2 = get_request_backoff(url = endpoint, query_string = clean_qs, max_retries = 3, back_off = 1.5)
            ## parse
            parsed_response2 = json.loads(response2.text)
            if verbose:
                print(nxt)
                print(parsed_response2)
            ## append
            response_list.append(parsed_response2)
            ## next page
            try:
                nxt = parsed_response2['nextPageToken']
            except:
                nxt = None
        ### Add missing claimReview metadata
        out = []
        ## start html session    
        session = requests_html.HTMLSession()
        for claim in response_list[0]['claims']:
            ## flatten the FC dict
            flat_google = flatten(claim, filter_regex = None)
            try:
                ## get the page with the FC
                fc_page = flat_google['claimReview.url']
                ## pull the missing claimReview JSON
                try:
                    cr = get_claimReview_meta(page = fc_page, html_session = session)
                except Exception as e:
                    print(f'Error retrieving the claimReview json from page({fc_page}): {e}')
                    cr = [{}]
                ## combine both dictionaries
                out.append({**flat_google, **cr[0]})
            except:
                ## just the data retrieved from the api
                out.append(flat_google)
        return out
               
### Run    
if __name__ == "__main__":
    ### define the relevant query parameters
    Q = 'coronavirus'
    # API_KEY = 'XXXXX' ## Your api key goes here
    LANG_CODE = None
    PAGESIZE = 100
    MAXDAYS = 5
    ### make the query
    out = google_claim_search(api_key = API_KEY, q = Q, lang_code = LANG_CODE, pagination_size = PAGESIZE, max_days_age = MAXDAYS)
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
    
    