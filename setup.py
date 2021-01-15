from setuptools import setup

with open("README.md", "r") as fh:
	long_description = fh.read()


setup(
      name='google-factCheck-helpers',
      version='0.1.0',
      author='José Reis',
      packages= ['google_fc_helpers'],
      description="helpers to make calls to google's claimSearch endpoint and fetch/parse claimReview json+ld from fact check pages",
      long_description=long_description,
      long_description_content_type="text/markdown",
      install_requires=[
              "lxml>=4.3.3",
              "requests_html>=0.10.0",
              "requests>=2.22.0",
              "extruct>=0.12.0"
             ],
      python_requires='>=3',
)
