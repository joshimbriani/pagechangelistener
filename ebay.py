import os
import time

from ebay_rest import API, Error
import google.generativeai as genai

import messaging

SEARCH_QUERY = '(Halloween Horror Nights, HHN)'
# There's no way that more than 20 new HHN items get posted to Ebay in a minute, right?
SEARCH_LIMIT = 20

# Looks like the eBay search adds seemingly random items based on like random IDs?
# So we'll do a little sanity checking and ensure that one of these words are in the 
# title. This only backfires when someone misspells *all* of them.
MUST_MATCH_IN_TITLE = ["hhn", "halloween", "horror", "nights"]

genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash')

def main():
    m = messaging.Messaging()

    # Get the list of seen item IDs.
    seen_ids = get_seen_ids()

    # Generate the list of eBay auctions.
    auction_items = get_auction_items()

    # Loop over all the auction items and skip the ones that we've seen already.
    for item in auction_items:
        item_id = item['legacy_item_id']
        if item_id not in seen_ids:
            item_title = item['title']
            matches = False
            for match in MUST_MATCH_IN_TITLE:
                matches |= (match in item_title.lower())
            
            seen_ids.append(item_id)

            if matches:
                time.sleep(5)
                response = get_classifier_decision(item_title.replace("\"", "\\\""))

                if "yes" in response:
                    # Send a notification.
                    m.send_message("Found eBay auction", f"title: \"{item_title}\"\nURL: {item['item_web_url']}")

    write_seen_ids(seen_ids)

def get_seen_ids():
    with open('seen_auction_items.txt', 'r') as f:
        contents = f.read().split()

    return contents

def get_auction_items():
    items = []
    item_ids = set()
    try:
        api = API(application='production_1', user='production_1', header='US')
    except Error as error:
        print(f'Error {error.number} is {error.reason} {error.detail}.\n')
    else:
        try:
            for record in api.buy_browse_search(q="Halloween Horror Nights", sort='newlyListed', limit=20):
                if 'record' not in record:
                    pass    # TODO Refer to non-records, they contain optimization information.
                else:
                    r = record['record']
                    if 'legacy_item_id' not in r:
                        continue
                    else:
                        if r['legacy_item_id'] not in item_ids:
                            item_ids.add(r['legacy_item_id'])
                            items.append(record['record'])
        except Error as error:
            print(f'Error {error.number} is {error.reason} {error.detail}.\n')
        else:
            pass

        try:
            for record in api.buy_browse_search(q="HHN", sort='newlyListed', limit=20):
                if 'record' not in record:
                    pass    # TODO Refer to non-records, they contain optimization information.
                else:
                    r = record['record']
                    if 'legacy_item_id' not in r:
                        continue
                    else:
                        if r['legacy_item_id'] not in item_ids:
                            item_ids.add(r['legacy_item_id'])
                            items.append(record['record'])
        except Error as error:
            print(f'Error {error.number} is {error.reason} {error.detail}.\n')
        else:
            pass

    return items

def write_seen_ids(seen_ids):
    with open('seen_auction_items.txt', 'w') as f:
        f.write('\n'.join(seen_ids))

def get_classifier_decision(title):
    with open('HHNMapStartingPrompt.txt') as f:
        prompt = f.read()

    response = model.generate_content(prompt.replace("[]", title))
    if not response.text or response.text.strip().lower() not in ["yes", "no"]:
        return "yes"

    return response.text.strip().lower()

if __name__ == "__main__":
    main()