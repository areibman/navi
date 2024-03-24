import re
from apify_client import ApifyClient

from litellm import completion
import os
from dotenv import load_dotenv
load_dotenv()


def find_link_in_string(s: str) -> str | None:
    # Regular expression to find URLs in a string
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    match = re.search(url_pattern, s)
    if match:
        return match.group()
    return None


def create_response(message: str, url: str | None = None) -> str:
    ...

    response = completion(
        # model="mistral/mistral-large-latest",
        model="groq/mixtral-8x7b-32768",
        messages=[
            {"role": "system", "content": f"""You are an information extraction model. Your purpose is to extract text from web pages and format it as following:
            
            Company name: [Company name]
            Website: [Website]
            Description: [Description]
            Tags: [Tags]
            Takeaways: [Key Takeaways]
            Questions: [Open Questions]
            
             
            This information will not be clean or organized. Your purpose is to do your best to summarize the information and read between the lines to be concise and informative.

            The website being scraped is: {url}

            Format it EXACTLY as follows. Example below:
---
*Company name*:
`Acme Corp`
---
*Website*:
`acmecorp.com`
---
*Description*:
`Company that does things.`
---
*Tags*:
`Manufacturing. Retail. E-commerce.`
---
*Takeaways*:
`Provides shareholders with value by selling products.`
---
*Questions*:
`What products do they sell? How do they make money? What is their market share?`
---

            """},

            {"role": "assistant", "content": "Confirmed. Please load web data:"},
            {"role": "user", "content":  message},]
    )
    return (response.choices[0].message.content)


# "groq/mixtral-8x7b-32768"


def scrape_site(url: str) -> str:
    # Initialize the ApifyClient with your API token
    client = ApifyClient(os.environ['APIFY_API_KEY'])

    # Prepare the Actor input
    run_input = {
        "startUrls": [{"url": url}],
        "useSitemaps": False,
        "crawlerType": "playwright:firefox",
        "includeUrlGlobs": [],
        "excludeUrlGlobs": [],
        "ignoreCanonicalUrl": False,
        "maxCrawlDepth": 0,
        "maxCrawlPages": 1,
        "initialConcurrency": 0,
        "maxConcurrency": 200,
        "initialCookies": [],
        "proxyConfiguration": {"useApifyProxy": True},
        "maxSessionRotations": 10,
        "maxRequestRetries": 5,
        "requestTimeoutSecs": 60,
        "dynamicContentWaitSecs": 10,
        "maxScrollHeightPixels": 5000,
        "removeElementsCssSelector": """nav, footer, script, style, noscript, svg,
    [role=\"alert\"],
    [role=\"banner\"],
    [role=\"dialog\"],
    [role=\"alertdialog\"],
    [role=\"region\"][aria-label*=\"skip\" i],
    [aria-modal=\"true\"]""",
        "removeCookieWarnings": True,
        "clickElementsCssSelector": "[aria-expanded=\"false\"]",
        "htmlTransformer": "readableText",
        "readableTextCharThreshold": 100,
        "aggressivePrune": False,
        "debugMode": True,
        "debugLog": True,
        "saveHtml": True,
        "saveMarkdown": True,
        "saveFiles": False,
        "saveScreenshots": False,
        "maxResults": 9999999,
        "clientSideMinChangePercentage": 15,
        "renderingTypeDetectionPercentage": 10,
    }

    # Run the Actor and wait for it to finish
    run = client.actor("aYG0l9s7dbB7j3gbS").call(run_input=run_input)

    # Fetch and print Actor results from the run's dataset (if there are any)
    text_data = ""
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        text_data += item.get('text', "") + "\n"

    average_token = 0.75
    max_tokens = 20000  # slightly less than max to be safe 32k
    text_data = text_data[:int(average_token * max_tokens)]
    return text_data


def format_output(output: str) -> dict:
    sections = [i.strip() for i in output.split("---") if i.strip()]
    formatted_output = {}
    for section in sections:
        if ':' in section:
            key, value = section.split(':', 1)
            formatted_output[key.strip()] = value.strip()
    return formatted_output


def update_csv(data: dict):
    # Replace commas with semicolons to avoid CSV format issues
    row_string = [val.replace(',', ';') for val in data.values()]
    with open('data.csv', 'a') as f:
        f.write(','.join(row_string) + '\n')
