#!/usr/bin/python
# -*- coding: utf-8 -*-

from instagram_scraper.app import InstagramScraper
import os
import shutil
import datetime
import configparser
import requests
import json

# Get env vars
target_username = os.environ.get('INSTAGRAM_SCRAPING_TARGET_USERNAME')
login_username = os.environ.get('INSTAGRAM_SCRAPING_LOGIN_USERNAME')
login_password = os.environ.get('INSTAGRAM_SCRAPING_LOGIN_PASSWORD')
latest_stamp_filename = '.' + os.sep + os.environ.get('INSTAGRAM_SCRAPING_LATEST_STAMP')
scraping_interval = int(os.environ.get('INSTAGRAM_SCRAPING_INTERVAL_MINUTES'))
discord_webhook_url = os.environ.get('INSTAGRAM_SCRAPING_DISCORD_WEBHOOK')
discord_webhook_wait_url = discord_webhook_url + '?wait=true'

# Set the other vars
profile_date = datetime.datetime.fromtimestamp(1286323200) # instagram-scraper will set this timestamp to profile related items. 
scraped_data_store = '.' + os.sep + target_username
config_section_users = 'users'
instagram_url_prefix_for_shortcode = 'https://www.instagram.com/tv/'

# Delete previous scraped data
try:
    shutil.rmtree(scraped_data_store)
except:
    pass

# Create timestamp to retrieve the latest posts only
query_date = datetime.datetime.now() - datetime.timedelta(minutes=scraping_interval)
#query_date = datetime.datetime.fromtimestamp(profile_date + 1)
print('Fetch data posted after the following timestamp:' + query_date.strftime('%Y/%m/%d %H:%M:%S'))
query_date_int = int(query_date.timestamp())
parser = configparser.ConfigParser()
parser.add_section(config_section_users)
parser.set(config_section_users, target_username, str(query_date_int))
with open(latest_stamp_filename, 'w') as file:
    parser.write(file)

# Scrape
scraper = InstagramScraper()
scraper.username = target_username
scraper.usernames = [target_username]
scraper.login_user = login_username
scraper.login_pass = login_password
scraper.latest_stamps = latest_stamp_filename
parser = configparser.ConfigParser()
parser.read(scraper.latest_stamps)
scraper.latest_stamps_parser = parser
scraper.latest = True
scraper.media_metadata = True
scraper.destination = scraped_data_store
scraper.authenticate_with_login()
scraper.scrape()

# Get each post from JSON and send it to Discord
try:
    with open(scraped_data_store + os.sep + target_username + '.json') as json_file:
        json_dict = json.load(json_file)
    json_dict['GraphImages'].reverse();
    for item in json_dict['GraphImages']:
        caption = ''
        for edge in item['edge_media_to_caption']['edges']:
            caption += edge['node']['text']
        instagram_post_url = instagram_url_prefix_for_shortcode + item['shortcode'] + '/'
        main_content = {'content': caption + '\n' + instagram_post_url}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(discord_webhook_url, json.dumps(main_content), headers = headers)
except:
    pass

# Sort binary items by created time
results = []
for root, dirs, files in os.walk(scraped_data_store):
    full_path_files = []
    for filename in files:
        path = os.path.join(root, filename)
        full_path_files.append(path)
    for filename in sorted(full_path_files, key=lambda f: os.stat(f).st_mtime):
        file_mtime = datetime.datetime.fromtimestamp(os.stat(filename).st_mtime)
        others, ext = os.path.splitext(filename)
        # Ignore profile related items and json
        if (file_mtime != profile_date) and (ext != '.json'):
            results.append(filename)

# Upload images separately because I'm getting bored :-P
for result_item in results:
     with open(result_item, 'rb') as f:
         f2 = f.read()
     item_blob = {'Image' : (os.path.basename(result_item), f2), }
     response = requests.post(discord_webhook_wait_url, files = item_blob)
