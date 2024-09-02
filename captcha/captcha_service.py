import json
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
import boto3
from botocore.exceptions import ClientError
from driver.driver_service import *
from scraper.static import *


def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']

        print("Secret String:", repr(secret))

        secret_json = json.loads(secret)
        return secret_json
    except ClientError as e:
        raise e
    except json.JSONDecodeError as json_err:
        print(f"Error decoding JSON: {json_err}")
        raise
    
def handle_captcha(captcha_type , driver):
    print(f"Handling captcha of type: {captcha_type}")
    
    captcha_handlers = {
        'image_text': handle_image_text_captcha,
    }
    
    handler = captcha_handlers.get(captcha_type)
    
    if handler:
        handler(driver)
    else:
        # > RAISE ERROR INSTEAD
        print(f"No handler available for captcha type: {captcha_type}")


def handle_image_text_captcha(driver):
    #! modify for dynamic captcha image selector passing
    #? for now ill keep it as static for amazon

    # secret = get_secret('AcessKey')


    textract_client = boto3.client(
        'textract',
        region_name='us-east-1'
    )

    attempt = 0

    print("attempting")
    
    while attempt < CAPTCHA_MAX_ATTEMPTS:
        attempt += 1
        try:
            captcha_image_element = wait_for_element(driver , By.CSS_SELECTOR , "div.a-row.a-text-center > img" , 10)
            captcha_image_url = captcha_image_element.get_attribute('src')
            captcha_image = requests.get(captcha_image_url).content

            response = textract_client.detect_document_text(
                Document={
                    'Bytes': captcha_image
                }
            )

            captcha_text = ''
            for item in response["Blocks"]:
                if item["BlockType"] == "LINE":
                    captcha_text += item["Text"]

            print(f"Solved CAPTCHA (Attempt {attempt}): '{captcha_text}'")

            input_element = wait_for_element(driver , By.CSS_SELECTOR , "#captchacharacters")
            input_element.send_keys(captcha_text)
            
            submit_button = wait_for_element_clickable(driver , By.CSS_SELECTOR , "button[type='submit'].a-button-text")
            submit_button.click()

            # Check if CAPTCHA is still present
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='a-row a-text-center']/img"))
                )
                print(f"CAPTCHA still present after attempt {attempt}. Retrying...")
                continue  # CAPTCHA is still present, so continue the loop to solve it again
            except:
                # CAPTCHA is not present, proceed to scrape the title and price
                break

        except Exception as e:
            print(f"Error during CAPTCHA solving attempt {attempt}: {str(e)}")
            # continue
            break

