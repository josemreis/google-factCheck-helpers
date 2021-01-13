# Wrapper to Google Fact Checking Tools API and Fake news metadata scraper

Pipeline: 

1. Wrapper to the [claimSearch endpoint](https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search). Query the [fact check explorer database](https://toolbox.google.com/factcheck/) and retrieve metadata on fact checks ([following claimReview schema](https://schema.org/ClaimReview));
2. Beyond the data provided by the API, scrapes missing fact check metadata, e.g. fake news source, from the fact check urls obtained from the JSON file ([claimReview schema](https://schema.org/ClaimReview)) - where this data is available.

