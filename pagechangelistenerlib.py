import json
from os import path
import re
from difflib import unified_diff

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
            if path.exists(golden_site_path):
                # Check and see if the golden file matches the returned code
                with open(golden_site_path) as f:
                    golden_contents = f.read()
                    new_contents = text_from_html(r.content)
                    if golden_contents != new_contents:
                        diff = make_diff(golden_contents, new_contents)
                        paste_url = make_paste(f"{site}\n{diff}", site[8:28])
                        send_page_change_message(site, paste_url)

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

def make_diff(golden_contents: str, new_contents: str) -> str:
    golden_contents_split = golden_contents.split("    ")
    new_contents_split = new_contents.split("    ")

    return '\n'.join(unified_diff(golden_contents_split, new_contents_split))

def make_paste(paste_contents: str, url_for: str) -> str:
    with open('creds.json') as f:
        creds = json.load(f)
        post_object = {
            'api_dev_key': creds["pastebin_key"],
            'api_option': 'paste',
            'api_paste_code': paste_contents,
            'api_paste_private': '1',
            'api_paste_expire_date': '1H',
            'api_paste_name': f'Diff Report for {url_for}'
        }
        r = requests.post('https://pastebin.com/api/api_post.php', data=post_object)
        return r.text

def send_page_change_message(site, paste_url):
    with open('creds.json') as f:
        creds = json.load(f)

        client = Client(creds["account_sid"], creds["auth_token"])
        body = "Site {} changed. See diff at {}".format(site, paste_url)
        message = client.messages.create(body=body, from_=creds["from_phone_num"], to=creds["to_phone_num"])
