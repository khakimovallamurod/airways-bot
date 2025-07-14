import os
from dotenv import load_dotenv
    
load_dotenv()

def get_token():
    TOKEN = os.getenv("TOKEN")
    if TOKEN is None:
        raise ValueError("TOKEN not found.")
    return TOKEN

def get_url():
    URL = os.getenv("URL")
    if URL is None:
        raise ValueError("URL not found.")
    return URL