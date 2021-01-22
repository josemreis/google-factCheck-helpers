#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 13 17:18:21 2021

@author: jmr
"""
import requests_html
import asyncio
from google_fc_helpers.claim_review_parser import *

class async_claim_review_parser:
    
    """ Instantiate async_claim_review_parser class. Runs an asynchronous scraper and returns the HTTP responses."""
    
    ### Fetch claim review data straight from the source urls
    def __init__(self, claim_dict_list : list, **kwargs):
        """ 
        Instantiate class fetch_metadata. 
        args:
            claim_dict_list : list of claim dictionaries obtained from google_fct_wrapper.run_query()
        returns:
            list of response objects or with claim_review_dictionaries
        """
        self.claim_dict_list = claim_dict_list
        ## attrs: additional
        for k in kwargs:
            setattr(self, k, kwargs[k])
        ## list to store the http responses
        self.response_list  = []
        ## list to store the cr dicts
        self.data = []
        ### run the async scraper
        return asyncio.run(self.claim_review_async())

    ### Retrieving the missing claimReview data from the FC websites
    ## asynchronous get requests for fetching the claimReviews from the websites
    async def async_get_task(self, s: requests_html.AsyncHTMLSession, claim_dict : dict):
        """ asynchronous http get request """
        if 'fact_check_url' in claim_dict.keys():
            url = claim_dict['fact_check_url']
            try:
                response = await s.get(url)
                return [response, claim_dict]
            except Exception as err:
                print(f'When fetching the html of {url}. Got the following error: {err}')
                pass
    
    async def claim_review_async(self):
        """ Run the scrapers asynchronously. Then clean and parse the claim review objects"""
        ## start an asyncronous session
        s = requests_html.AsyncHTMLSession()
        ## define the tasks
        tasks = []
        ## fetch the urls
        for d in self.claim_dict_list:
            tasks.append(self.async_get_task(s = s, claim_dict = d))
        ## fetch the data async
        raw = await asyncio.gather(*tasks)
        ## fetch and clean the claim_review_data
        # instantiate a parser
        parser = claim_review_parser()
        out = []
        for task_list, url in zip(raw, self.claim_dict_list):
            try:
                response = task_list[0]
                self.response_list.append(response)
                if parser.check_claim_review(response):
                    parsed_html = response.content
                    try:
                        parsed_cr = parser.parse_claim_review(html = parsed_html, url = url)
                        print(parsed_cr)
                    except Exception as err:
                        print(f'Error occurred in the async claim review parser: {err}.')
                        parsed_cr = None
                        pass
                    if parsed_cr is not None:
                        cleaned = parser.clean_claim_review(cr = parsed_cr)
                        ## combine the dictionaries
                        new_d = {**task_list[1], **cleaned}
                        ## append
                        out.append(new_d)
                    else:
                        out.append(task_list[1])
            except:
                pass
        ## assign to attrivute
        self.data = out
            




