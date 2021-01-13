
from requests.exceptions import HTTPError
import time
from requests_html import AsyncHTMLSession
import requests
import json
from itertools import product

class google_fct_wrapper(object):
    
    def __init__(self, api_key = None, q = None, lang_code = None, reviewer_domain_filter = None, max_days_age = None, pagination_size = 100, pagination_token = None, pagination_offset = None, log_path = None):
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
        self.logfilename = log_path
        ## set up the logger
        logging.basicConfig(filename= self.logfilename, format='%(levelname)s : %(asctime)s : %(message)s', level=logging.DEBUG)
    
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
                    if self.logfilename is not None:
                        logging.info(f'Making query to claim search endpoint\nq:{q}\nmax_days_age:{self.max_days_age}\nreviewer_domain_filter:{reviewer_domain_filter}\n')
                    response = requests.get(url = endpoint, params = {k: v for k, v in querystring.items() if v is not None})
                    response.raise_for_status()
                    if verbose:
                        print(f'API Call to claim search endpoint. Status-code: {str(response.status_code)}\n')
                    break
                except HTTPError as http_err:
                    time.sleep(sleep_time)
                    print(f'HTTP error in API call occurred: {http_err}.\n - Retrying in {sleep_time} secs.')  
                    if self.logfilename is not None:
                        logging.error(f'HTTP error in API call: {http_err}')
                except Exception as err:
                    if self.logfilename is not None:
                        logging.error(f'Another non HTTP in API call error occurred: {err}')
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
            if self.logfilename is not None:
                        logging.info(f'No data retrieved for the query:\nq:{q}\nmax_days_age:{self.max_days_age}\nreviewer_domain_filter:{reviewer_domain_filter}\n')
            print(f'No data retrieved for the query:\nq:{q}\nmax_days_age:{self.max_days_age}\nreviewer_domain_filter:{reviewer_domain_filter}\n')
        return out