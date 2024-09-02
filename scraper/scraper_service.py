import re
from urllib.parse import urlparse
import requests
import random
import requests
from bs4 import BeautifulSoup
import re
import requests
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import time
import random
from scraper.static import *
from captcha.captcha_service import *
from driver.driver_service import *
def get_valid_proxy(proxy_file):
    """
    Reads the proxies from the proxy file, shuffles them, 
    and returns a list of valid HTTP/HTTPS proxies.
    """
    try:
        with open(proxy_file, 'r') as f:
            proxies = f.read().splitlines()

        if not proxies:
            return {"error": "Proxy file is empty or contains no valid proxies"}
        
        random.shuffle(proxies)
        return {"proxies": proxies}
    
    except FileNotFoundError:
        return {"error": f"Proxy file '{proxy_file}' not found."}
    
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}
def get_response(url):
    max_retries = GET_RESPONSE_MAX_ATTEMPS
    proxies_json = get_valid_proxy(PROXY_FILE)

    if "error" in proxies_json:
        return {"error": proxies_json['error']}
    
    proxies = proxies_json['proxies']
    retry_count = 0

    for proxy in proxies:
        if retry_count >= max_retries:
            return {"error": f"Reached maximum retry limit of {max_retries}."}
        
        scheme, proxy_address = proxy.split('://')
        proxy_dict = {scheme: f"{scheme}://{proxy_address}"}
        
        try:
            response = requests.get(url, proxies=proxy_dict, timeout=PROXY_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            retry_count += 1
            last_error = str(e)
    
    return {"error": f"All proxies failed after {max_retries} retries.", "last_error": last_error}
def extract_company_name(url):
    """Extracts the company name (domain) from the netloc."""
    netloc = urlparse(url).netloc
    company_name = netloc.lower().replace("www.", "").replace(".com", "")
    print(f"Extracted company name: {company_name}")
    return company_name
def dynamic_bs4(url):
    
    domain = extract_company_name(url)  # assuming url already validated
    config = CONFIG_BS4[domain]

    response = get_response(url)
    if not response:
        return {"error": "No response"}

    soup = BeautifulSoup(response.content, "html.parser")

    # TODO 
    # optional Best practice config

    # > mandatory config
    description_selector = config["description_selector"]
    price_selector = config["price_selector"]

    description_element = soup.select_one(description_selector)
    description = description_element.get_text(strip=True) if description_element else "Description not found"
    
    if isinstance(price_selector, list):
        # Combine the text from each part to form the full price
        # TODO make this a function
        price_parts = [soup.select_one(selector).get_text(strip=True) for selector in price_selector if soup.select_one(selector)]
        price = ''.join(price_parts) if price_parts else "Price not found"
    else:
        price_element = soup.select_one(price_selector)
        price = price_element.get_text(strip=True) if price_element else "Price not found"

    # > return values
    return {
        "price": price,
        "description": description
    }

# TODO review
def dynamic_selenium(url):
    driver = None
    try:
        domain = extract_company_name(url)  # Assuming url is already validated
        config = CONFIG_SELENIUM[domain]

        driver = chrome_driver_setup()
        driver.get(url)

        if "captcha" in config:
            captcha_type = config["captcha"]
            handle_captcha(captcha_type, driver)

        description_selector = config["description_selector"]
        price_selector = config["price_selector"]

        description_element = wait_for_element(driver, By.CSS_SELECTOR, description_selector)

        price = None
        if isinstance(price_selector, list):
            price_symbol = ""
            price_whole = ""
            price_fraction = ""
            
            for selector in price_selector:
                element = wait_for_element(driver, By.CSS_SELECTOR, selector)
                if element:
                    text = element.text.strip()
                    if selector.endswith("symbol"):
                        price_symbol = text
                    elif selector.endswith("whole"):
                        price_whole = text
                    elif selector.endswith("fraction"):
                        price_fraction = text
            
            if price_whole and price_fraction:
                price = f"{price_symbol}{price_whole}.{price_fraction}"
            elif price_whole:
                price = f"{price_symbol}{price_whole}"
        else:
            price_element = wait_for_element(driver, By.CSS_SELECTOR, price_selector)
            price = price_element.text.strip() if price_element else "Price not found"

        return {
            "price": price if price else "Price not found",
            "description": description_element.text.strip() if description_element else "Description not found"
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        return {"price": "Error", "description": "Error"}

    finally:
        if driver:
            driver.quit()

def fetch_product(url):
    company_name = extract_company_name(url)
    
    # Debugging: Check which company is being matched
    print(f"Checking company name: {company_name}")
    
    if company_name in CONFIG_BS4:
        print(f"Company found in known_companies: {company_name}")
       
        handler_function = dynamic_bs4(url)
        return handler_function
    
    if company_name in CONFIG_SELENIUM:
        print(f"Company found in known_companiess: {company_name}")
        handler_function2 = dynamic_selenium(url)
        return handler_function2
    
    else:
        print(f"Company not supported: {company_name}")
        return {"error": f"Company not supported: {company_name}"}
    




def generate_prompt(user_price, scraped_price, score):
    """
    Generate a prompt for the Claude model to compare user-provided price with scraped price,
    focusing solely on price comparison and providing a brief two-line analysis.
    """
    prompt = f"""
    <prompt>
        <task>Price Comparison</task>

        <examples>
            <example>
                <userProvidedPrice>100.00</userProvidedPrice>
                <scrapedPrice>100.00</scrapedPrice>
                <matchScore>100</matchScore>
                <analysis>The prices are exactly the same, resulting in a perfect match score of 100.</analysis>
            </example>
            <example>
                <userProvidedPrice>100.00</userProvidedPrice>
                <scrapedPrice>95.00</scrapedPrice>
                <matchScore>95</matchScore>
                <analysis>The scraped price is slightly lower than the user-provided price, resulting in a high match score of 95.</analysis>
            </example>
            <example>
                <userProvidedPrice>100.00</userProvidedPrice>
                <scrapedPrice>80.00</scrapedPrice>
                <matchScore>80</matchScore>
                <analysis>There is a noticeable difference between the user-provided price and the scraped price, leading to a lower match score of 80.</analysis>
            </example>
        </examples>
        
        <userProvidedPrice>{user_price}</userProvidedPrice>
        <scrapedPrice>{scraped_price}</scrapedPrice>
        <matchScore>{score}</matchScore>
        <detailedAnalysis>
            <description>Provide only a brief two-line analysis focused on the price comparison. Avoid any additional details.</description>
        </detailedAnalysis>
        
        <outputFormat>
            <format type="JSON">
                <![CDATA[
                {{
                    "match_score": {score},
                    "analysis": "Your concise, two-line analysis of the price comparison here."
                }}
                ]]>
            </format>
        </outputFormat>
    </prompt>
    """
    return prompt.strip()
import re

def extract_numerical_price(price_str):
    cleaned_price_str = re.sub(r'[^\d\.]', '', price_str)
    
    match = re.search(r'\d+\.?\d*', cleaned_price_str)
    
    if match:
        extracted_price = float(match.group())
        print(f"Extracted numerical price: {extracted_price}")
        return extracted_price
    else:
        print(f"Price string: {price_str}")
        raise ValueError("No numerical part found in the price string."+price_str)

def calculate_match_score(user_price, scraped_price):
   
    user_price = float(user_price)
    fscraper_price = float(scraped_price)
    
    print(f"Comparing User price: {user_price} with Scraped price: {fscraper_price}")
    
    
    absolute_difference = abs(user_price - fscraper_price)
    print(f"Absolute difference: {absolute_difference}")
    percentage_difference = (absolute_difference / user_price) * 100
    print(f"Percentage difference: {percentage_difference}")
    score = max(0, 100 - percentage_difference)
    print(f"Calculated score: {score}")
    
   
    return int(score)

def get_completion(prompt):
    try:
        # bedrock = boto3.client(service_name="bedrock-runtime", region_name=REGION_NAME)
        bedrock = boto3.client(service_name="bedrock-runtime", region_name='us-west-2')
        body = json.dumps({
            "max_tokens": 100,  # Limit the response length to avoid excess details
            "messages": [{"role": "user", "content": prompt}],
            "anthropic_version": "bedrock-2023-05-31"
        })

        response = bedrock.invoke_model(body=body, modelId=MODEL_NAME)
        response_body = json.loads(response.get("body").read())
        return response_body.get("content")
    except Exception as e:
        print(f"Error communicating with Claude: {e}")
        raise e

