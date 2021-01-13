#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 13 17:18:21 2021

@author: jmr
"""
import requests_html
import asyncio
from claim_review_parser import *

class async_claim_review_parser:
    
    """ Instantiate async_claim_review_parser class. Runs an asynchronous scraper and returns the HTTP responses."""
    
    ### Fetch claim review data straight from the source urls
    def __init__(self, urls: list, **kwargs):
        """ 
        Instantiate class fetch_metadata. 
        args:
            urls: list, list of urls
        returns:
            list of response objects or with claim_review_dictionaries
        """
        self.urls = urls
        ## attrs: additional
        for k in kwargs:
            setattr(self, k, kwargs[k])
        ## list to store the http responses
        self.response_list  = []
        ## list to store the cr dicts
        self.cr_list = []
        ### run the async scraper
        return asyncio.run(self.claim_review_async())

    ### Retrieving the missing claimReview data from the FC websites
    ## asynchronous get requests for fetching the claimReviews from the websites
    async def async_get_task(self, s: requests_html.AsyncHTMLSession, url: str):
        """ asynchronous http get request """
        response = await s.get(url)
        return response
    
    async def claim_review_async(self):
        """ Run the scrapers asynchronously. Then clean and parse the claim review objects"""
        ## start an asyncronous session
        s = requests_html.AsyncHTMLSession()
        ## define the tasks
        tasks = []
        for url in self.urls:
            tasks.append(self.async_get_task(s = s, url = url))
        ## fetch the data async
        raw = await asyncio.gather(*tasks)
        ## fetch and clean the claim_review_data
        # instantiate a parser
        parser = claim_review_parser()
        out = []
        for response, url in zip(raw, self.urls):
            if parser.check_claim_review(response):
                parsed_html = response.content
                try:
                    parsed_cr = parser.parse_claim_review(html = parsed_html, url = url)
                    print(parsed_cr)
                except Exception as err:
                    print(f'Error occurred in the async claim review parser: {err}.')
                    pass
                if parsed_cr is not None:
                    cleaned = parser.clean_claim_review(cr = parsed_cr)
                    ## append
                    out.append(cleaned)
        ## assign to attrivute
        self.cr_list = out
            




