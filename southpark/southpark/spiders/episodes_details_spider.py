import scrapy
import csv

#SPIDER SCRAPS DATA FROM TABLE UNDER EPISODES SECTION

class episode_details_spider(scrapy.Spider):
    name = 'episode_details_spider'
    start_urls = ['https://en.wikipedia.org/wiki/List_of_South_Park_episodes']

    def __init__(self, *args, **kwargs):
        super(episode_details_spider, self).__init__(*args, **kwargs)
        self.existing_links = set()

        # Path to the CSV file
        csv_file_path = '/home/alvcantu/southpark/etl/raw_episode_details.csv'

        # Read the CSV file and store the title_link values in a set
        try:
            with open(csv_file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'title_link' in row:
                        self.existing_links.add(row['title_link'])
        except FileNotFoundError:
            self.log(f"File not found: {csv_file_path}")
        except Exception as e:
            self.log(f"Error reading file {csv_file_path}: {e}")

    def parse(self, response):
        # Select all the tables under the "Episodes" section
        episodes_tables = response.xpath('//span[@id="Episodes"]/following::table[contains(@class, "wikitable plainrowheaders wikiepisodetable")]')

        for table in episodes_tables:
            # Iterate through rows of the table
            rows = table.xpath('.//tr')[1:]  # Skip the header row
            for row in rows:
                cells = row.xpath('.//td')

                # Update title and title_link extraction logic
                title_cell = row.xpath('.//td[@class="summary"]//a')
                title = title_cell.xpath('text()').get().strip().replace('"', '') if title_cell else None
                href = title_cell.xpath('@href').get().strip() if title_cell else None
                full_href = response.urljoin(href).replace('"', '') if href else None

                # Extract date with additional class check, ""bday dtstart published updated itvstart" for specials, "bday dtstart published updated" for regular.
                date = (row.xpath('.//span[@class="bday dtstart published updated itvstart"]/text() | .//span[@class="bday dtstart published updated"]/text()')
                 .get() or row.xpath('.//td[4]/text()').get() or '').strip().replace('"', '')


                # Check for prod_code, set to "Special" if not present, need to reformat in ETL.
                prod_code_cell = cells[5] if len(cells) > 5 else None
                prod_code = prod_code_cell.xpath('text()').get().strip().replace('"', '') if prod_code_cell and prod_code_cell.xpath('text()') else "Special"

                if full_href and full_href not in self.existing_links:
                    episode_data = {
                        'episode_id': row.xpath('.//th[@scope="row"]/text()').get().strip().replace('"', '') if row.xpath('.//th[@scope="row"]/text()') else '',
                        'title': title,
                        'title_link': full_href,
                        'date': date,
                        'prod_code': prod_code
                    }
                    yield episode_data
