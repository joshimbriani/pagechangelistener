import json
from os import path
import re

from bs4 import BeautifulSoup
from bs4.element import Comment
import requests
from twilio.rest import Client

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

def run():
    for site in get_watch_urls():
        site = site.rstrip('\n')
        if not re.compile(URL_REGEX).match(site):
            continue
        r = requests.get(site)
        if r:
            golden_site_path = path.join('goldens', site.replace("/", "-")
                    + ".txt")
            print(golden_site_path)
            if path.exists(golden_site_path):
                # Check and see if the golden file matches the returned code
                with open(golden_site_path) as f:
                    if f.read() != text_from_html(r.content):
                        send_page_change_message(site)

            # Update file
            with open(golden_site_path, "w") as f:
                f.write(text_from_html(r.content))

def get_watch_urls():
    with open('urls.txt') as f:
        for line in f:
            yield line

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    texts = soup.findAll(text=True)
    visible_texts = filter(tag_visible, texts)  
    return u" ".join(t.strip() for t in visible_texts)

def send_page_change_message(site):
    with open('creds.json') as f:
        creds = json.load(f)

        client = Client(creds["account_sid"], creds["auth_token"])
        body = "Site {} changed".format(site)
        message = client.messages.create(body=body, from_=creds["from_phone_num"], to=creds["to_phone_num"])
