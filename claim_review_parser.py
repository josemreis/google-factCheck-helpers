#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan  9 22:44:13 2021

@author: jmr
"""
import extruct
import requests
from lxml import html
from requests.exceptions import HTTPError
import time

class claim_review_parser(object):
    
    """
        Scrapes and parses claim review schema from websites adopting it. 
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
        
    def scrape(self, url: str, max_retries: int, back_off: float):
        """ Scrape a website and parse html"""
        attempts = 0
        response = None
        while attempts < max_retries:
            attempts += 1
            sleep_time = round(attempts ** back_off, 1)
            try:
                response = requests.get(url = url)
                response.raise_for_status()
                break
            except HTTPError as http_err:
                print(f'HTTP Error {http_err}. Retrying in {sleep_time} secs.')
                time.sleep(sleep_time)
            except Exception as err:
                raise ValueError(f'Another non HTTP Request error occurred: {err}.')
        return response
        
    def check_claim_review(self, response = None):
        """Given a HTTP response, check wether or not a page uses claim_review schema """
        ## parse the content
        content = html.fromstring(response.content)
        ## check whether the script tag with the claimReview exists
        claim_review_script = content.xpath('//script[@type="application/ld+json" and contains(text(), "itemReviewed")]')
        return len(claim_review_script) > 0
    
    def fetch_html(self, response = None):
        return response.text
    
    def parse_claim_review(self, html: bytes, url: str):
        """Fetch JSON-LD structured data."""
        ## parse the json linked data metadata
        metadata = extruct.extract(
            html,
            base_url=url,
            syntaxes=['json-ld'],
            uniform=True
        )['json-ld']
        ## select only the claimReview dictionary where more than one exists
        out = []
        if isinstance(metadata, list) and len(metadata) > 0:
            for d in metadata:
                if '@graph' in d.keys() and isinstance(d['@graph'], list):
                    if isinstance(d['@graph'], list):
                        out.append(d['@graph'][0])
                    else:    
                        out.append(d['@graph'])
                else:
                    if 'itemReviewed' in d.keys() and isinstance(d, dict):
                        out.append(d)
        elif len(metadata) > 0:
            out = [metadata]
        else:
            out = [None]
        return out[0]
    
    def get_candidate_value(self, d: dict, key: str, candidate_expressions = None):
        """ 
        Fetch the value given a key or one of a list of possible candidate keys or key[index] combos as expressions to be dynamically evaluated
        args:
            d: dict,
            key: str, 
            candidate_expressions: list of str, containing python code to be dynamically evaluated
        """
        try:
            if d.get(key) is None:
                out = None
                if candidate_expressions is not None:
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
        except:
            out = None
        return out
    
    def clean_claim_review(self, cr: dict):
        """ Extract the relevant metadata """
        ### fetch the main arrays
        rr_dict = self.get_candidate_value(cr, 'reviewRating')
        ir_dict = self.get_candidate_value(cr, 'itemReviewed')
        author = self.get_candidate_value(cr, 'author')
        return dict(
                claim_reviewed = self.get_candidate_value(cr, 'claimReviewed'),
                review_rating_type = self.get_candidate_value(rr_dict, '@type'),
                review_rating_value = self.get_candidate_value(rr_dict, 'ratingValue'),
                review_rating_best = self.get_candidate_value(rr_dict, 'bestRating'),
                review_rating_worst = self.get_candidate_value(rr_dict, 'worstRating'),
                review_rating_alternate_name = self.get_candidate_value(rr_dict, 'alternateName'),
                fact_check_url = self.get_candidate_value(cr, 'url'),
                fact_check_date_published = self.get_candidate_value(cr, 'datePublished'),
                fact_check_author_type = self.get_candidate_value(author, '@type'),
                fact_check_author_id = self.get_candidate_value(author, '@id'),
                fact_check_author_name = self.get_candidate_value(author, 'name'),
                fact_check_author_url = self.get_candidate_value(author, 'url'),
                fact_check_author_url_sameAs = self.get_candidate_value(author, 'sameAs', candidate_expressions = ['["sameAs"][0]']),
                item_reviewed_url = self.get_candidate_value(ir_dict, 'url', candidate_expressions = ['["author"]["sameAs"]["url"]', '["author"]["sameAs"]', '["appearance"]', '["appearance"]["url"]']),
                item_reviewed_date_published = self.get_candidate_value(ir_dict, 'datePublished', candidate_expressions = ['["author"]["datePublished"]', '["appearance"]["datePublished"]']),
                item_reviewed_author_type = self.get_candidate_value(ir_dict, 'author.type', candidate_expressions = ['["author"]["@type"]', '["author"]["type"]']),
                item_reviewed_author_name = self.get_candidate_value(ir_dict, 'author.name', candidate_expressions = ['["author"]["name"]'])
                )
