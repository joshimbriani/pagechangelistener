import json
from os import path
import re
from difflib import unified_diff

from bs4 import BeautifulSoup
from bs4.element import Comment
import requests
from twilio.rest import Client
import praw

import messaging

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

def run():
    m = messaging.Messaging()
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
                        send_page_change_message(m, site, paste_url)

            # Update file
            with open(golden_site_path, "w") as f:
                f.write(text_from_html(r.content))

    # Handle Reddit specially
    all_sites_and_terms = get_partial_page_change_urls_and_terms()
    reddit = make_reddit()
    for subreddit in all_sites_and_terms["reddit"]:
        submissions = []
        for submission in reddit.subreddit(subreddit["name"]).new(limit=20):
            submissions.append(submission.title)

        all_submissions = "\n".join(submissions)
        golden_path = path.join('goldens', 'reddit', subreddit["name"] + '.txt')
        if path.exists(golden_path):
            with open(golden_path) as f:
                golden_contents = f.read()
                for term in subreddit["terms"]:
                    if term.lower() in all_submissions.lower() and term.lower() not in golden_contents.lower():
                        send_reddit_change_message(m, term, subreddit["name"])

        with open(golden_path, "w") as f:
                f.write(all_submissions)
    

def get_watch_urls():
    with open('urls.txt') as f:
        for line in f:
            yield line

def get_partial_page_change_urls_and_terms():
    with open('partial_page_changes.json', "r") as f:
        return json.loads(f.read())

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

def send_page_change_message(m, site, paste_url):
    with open('creds.json') as f:
        creds = json.load(f)

        client = Client(creds["account_sid"], creds["auth_token"])
        body = "Site {} changed. See diff at {}".format(site, paste_url)
        # Send both a notification and a text for now.
        m.send_message("Page Change", body)
        message = client.messages.create(body=body, from_=creds["from_phone_num"], to=creds["to_phone_num"])

def send_reddit_change_message(m, term, subreddit_name):
    with open('creds.json') as f:
        creds = json.load(f)

        client = Client(creds["account_sid"], creds["auth_token"])
        body = f"Found a match for term {term} on https://old.reddit.com/r/{subreddit_name}/"
        
        # Send both a notification and a text for now.
        m.send_message("Reddit Watched Term Found", body)
        message = client.messages.create(body=body, from_=creds["from_phone_num"], to=creds["to_phone_num"])

def make_reddit():
    with open('creds.json') as f:
        creds = json.load(f)

        return praw.Reddit(
            client_id=creds["reddit_client_id"],
            client_secret=creds["reddit_client_secret"],
            user_agent="PageChangeListenerJEI"
        )
