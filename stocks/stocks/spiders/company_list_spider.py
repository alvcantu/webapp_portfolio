import scrapy

class company_list_spider(scrapy.Spider):
    name = 'company_list_spider'
    start_urls = ['https://en.wikipedia.org/wiki/List_of_public_corporations_by_market_capitalization']

    # Set custom settings so the output of this spider is exported to a csv that is later used in to transform the data.
    custom_settings = {
        'FEED_FORMAT': 'csv',
        'FEED_URI': 'file:///home/alvcantu/stocks/etl/raw_company_list_url.csv',
        'FEED_EXPORT_FIELDS': ['company_url', 'ticker', 'ticker_url'],
        'FEED_EXPORTERS': {
            'csv': 'scrapy.exporters.CsvItemExporter',
        },
        'FEED_EXPORT_PARAMS': {
            'delimiter': ',',
            'quotechar': '"',
            'headers': ['company_url', 'ticker', 'ticker_url'],
        },
        'FEEDS': {
            'file:///home/alvcantu/stocks/etl/raw_company_list_url.csv': {
                'format': 'csv',
                'overwrite': True,
            },
        },
    }

    # Spider instructions begins here

    # # First extract links from the table in 'List_of_public_corporations_by_market_capitalization' wiki page.
    def parse(self, response):
        # Find the table using its class
        table = response.xpath("//table[contains(@class, 'wikitable sortable')]")
        print(f"Table found: {table}")

        # Extract rows, skipping the header rows
        rows = table.xpath('.//tr[position()>2]')
        print(f"Number of rows: {len(rows)}")

        for row in rows:
            href = row.xpath('.//td[1]//a/@href').get()
            if href:
                full_url = response.urljoin(href)
                print(f"Found URL: {full_url}")
                yield scrapy.Request(full_url, callback=self.parse_company_page)

    # Once links are extracted, crawl each link to extract the ticker symbol located on the right hand box of each wiki page.
    def parse_company_page(self, response):
        # Find the "Traded as" row in the infobox
        traded_as_row = response.xpath('//th[contains(@class, "infobox-label")]/div/a[@title="Ticker symbol"]/ancestor::tr')

        if traded_as_row:
            # Extract all links in traded row section
            ticker_links = traded_as_row.xpath('.//td[contains(@class, "infobox-data")]//a')

            for link in ticker_links:
                ticker = link.xpath('./text()').get()
                ticker_url = link.xpath('./@href').get()

                # Check if this link is within parentheses to avoid problem of multiple Class of stocks as is case for Alphabet Inc.
                preceding_text = link.xpath('./preceding-sibling::text()').get()
                following_text = link.xpath('./following-sibling::text()').get()

                if not (preceding_text and '(' in preceding_text[-5:]) and not (following_text and ')' in following_text[:5]):
                    # Only keep the ticker if its URL starts with 'https://', referring to an actual stock market website
                    if ticker_url.startswith('https://'):
                        yield {
                            'company_url': response.url,
                            'ticker': ticker,
                            'ticker_url': ticker_url
                        }
                        # Break after finding the first valid ticker
                        break