import scrapy
import pandas as pd
import csv

#SPIDER SCRAPS ALL EPISODE WIKI ARTICLES
#EXTRACTS FIRST SECTION OF ARTICLE AS SUMMARY
#CHECKS WHICH CHARACTERS APPEAR IN THE WHOLE ARTICLE AND EXTRACTS THEM.
#APPENDS NEW LINKS ONLY

class episode_loop_spider(scrapy.Spider):
    name = 'episode_loop_spider'

    def __init__(self, *args, **kwargs):
        super(episode_loop_spider, self).__init__(*args, **kwargs)
        self.df_episode_details = pd.read_csv('/home/alvcantu/southpark/etl/raw_episode_details.csv')
        self.df_character_details = pd.read_csv('/home/alvcantu/southpark/etl/stg_character_details.csv')
        self.character_ids = self.df_character_details['character_id'].tolist()

        # Read existing scraped URLs
        self.existing_urls = set()
        try:
            with open('/home/alvcantu/southpark/etl/raw_episode_loop.csv', 'r') as f:
                reader = csv.DictReader(f)
                self.existing_urls = set(row['title_link'] for row in reader)
        except FileNotFoundError:
            self.logger.info("raw_episode_loop.csv not found. Will create a new file.")

        #Filter start_urls to only include new URLs
        all_urls = set(self.df_episode_details['title_link'].tolist())
        new_urls = all_urls - self.existing_urls
        self.start_urls = list(new_urls)

        self.logger.info(f"Total URLs in raw_episode_details.csv: {len(all_urls)}")
        self.logger.info(f"Existing URLs: {len(self.existing_urls)}")
        self.logger.info(f"New URLs to scrape: {len(self.start_urls)}")

    def parse(self, response):
        # Extract the first paragraph of the main article body
        #first_section = response.css('#mw-content-text .mw-parser-output > p').get()

        # Extract the first non-empty paragraph of the main article body
        paragraphs = response.css('#mw-content-text .mw-parser-output > p')
        first_section = None
        for p in paragraphs:
            if p.get() and not p.css('.mw-empty-elt'):
                first_section = p.get()
                break

        if first_section is None:
            self.logger.warning(f"No valid summary found for {response.url}")
            first_section = ""  # or you could set it to some default value

        # Find all character IDs mentioned in the article
        article_text = response.css('#mw-content-text .mw-parser-output').getall()
        article_text = ' '.join(article_text)
        mentioned_characters = [char_id for char_id in self.character_ids if str(char_id) in article_text]

        data = {
            'title_link': response.url,
            'summary': first_section,
            'mentioned_character_ids': mentioned_characters
        }

        # Append the new data to the CSV file
        with open('/home/alvcantu/southpark/etl/raw_episode_loop.csv', 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['title_link', 'summary', 'mentioned_character_ids'])
            if f.tell() == 0:  # File is empty, write header
                writer.writeheader()
            writer.writerow(data)

        yield data

    def closed(self, reason):
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Processed {len(self.start_urls)} new URLs")
