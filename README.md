# Wrapper to Google Fact Checking Tools API and Fake news metadata scraper

1. Wrapper to the [claimSearch endpoint](https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search). Query the [fact check explorer database](https://toolbox.google.com/factcheck/) and retrieve metadata on fact checks ([following claimReview schema](https://schema.org/ClaimReview));
2. Beyond the data provided by the API, scrapes missing fact check metadata, e.g. fake news source, from the fact check urls obtained from the JSON file ([claimReview schema](https://schema.org/ClaimReview)) - where this data is available.

Installation
------------

You can install directly from the GitHub repository:

    pip install git+https://github.com/josemreis/google-factCheck-helpers


Example usage
-------------

```python3
from google_fc_helpers.google_fc_wrapper import *
from google_fc_helpers.async_scraper import *
import json

### google fct call
## prep the query
query = {
        "key": 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
        "query": ["covid", "Coronavirus"],
        "languageCode" : ['pt', 'es', 'en', 'de'],
        "reviewPublisherSiteFilter": None,
        "pageSize": 50,
        "maxAgeDays": 2
        }
# query = '/home/jmr/Desktop/example_query.json' # alternatively, feed it the query in json format
## make the call
cs = claim_search(query = query)
## run it
google_data = cs.run_query()
### fetch claim review metadata asynchronously
claim_review_data = async_claim_review_parser(claim_dict_list = google_data)
### export
with open('fake_news.json', 'w') as f:
    json.dump(claim_review_data.data, f, ensure_ascii=False, indent=4)
```


**Example output**

```json
{
        "query": "covid",
        "languageCode": "pt",
        "reviewPublisherSiteFilter": null,
        "maxAgeDays": 10,
        "query_date": "2021-01-13",
        "claim_reviewed": "Brasileiros criaram máquina que faz testes de covid-19 quase sem custo",
        "claimant": "Posts nas redes sociais",
        "claim_date": "2021-01-06T18:16:03Z",
        "fact_check_url": "https://politica.estadao.com.br/blogs/estadao-verifica/brasileiros-criaram-maquina-de-testes-de-covid-19-mas-produto-ainda-esta-em-testes-e-nao-tem-preco/",
        "fact_check_domain": "politica.estadao.com.br",
        "fact_check_author_name": "Estadão",
        "fact_check_title": "Brasileiros criaram máquina de testes de covid-19, mas produto ...",
        "fact_check_language_code": "pt",
        "review_rating_type": "Rating",
        "review_rating_value": "3",
        "review_rating_best": 5,
        "review_rating_worst": null,
        "review_rating_alternate_name": "Verdadeiro em partes",
        "fact_check_date_published": "2021-01-06T15:16:03-03:00",
        "fact_check_author_type": "Organization",
        "fact_check_author_id": null,
        "fact_check_author_url": null,
        "fact_check_author_url_sameAs": null,
        "item_reviewed_url": "https://politica.estadao.com.br/blogs/estadao-verifica/brasileiros-criaram-maquina-de-testes-de-covid-19-mas-produto-ainda-esta-em-testes-e-nao-tem-preco/",
        "item_reviewed_date_published": "2021-01-06T15:16:03-03:00",
        "item_reviewed_author_type": "Organization",
        "item_reviewed_author_name": "Posts nas redes sociais"
 }

```


Links
-----

- [Google's claimSearch endpoint docs](https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search)
- [More on ClaimReview](https://www.claimreviewproject.com/the-facts-about-claimreivew)
- [ClaimReview schema](https://schema.org/ClaimReview)
