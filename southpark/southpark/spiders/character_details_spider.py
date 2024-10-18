import scrapy
import csv

#SPIDER SCRAPS ALL CHARACTERS FROM TWO SECTIONS OF THE WIKIPEDIA ARTICLE
#APPENDS NEW CHARACTERS ONLY

class character_details_spider(scrapy.Spider):
    name = 'character_details_spider'
    start_urls = ['https://en.wikipedia.org/wiki/List_of_South_Park_characters']
    custom_settings = {
        'FEED_FORMAT': 'csv',
        'FEED_URI': '/home/alvcantu/southpark/etl/raw_character_details.csv'
    }

    def __init__(self, *args, **kwargs):
        super(character_details_spider, self).__init__(*args, **kwargs)
        self.existing_characters = set()

        # Path to the CSV file
        csv_file_path = '/home/alvcantu/southpark/etl/raw_character_details.csv'

        # Read the CSV file and store the character_name values in a set
        try:
            with open(csv_file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'character_name' in row:
                        self.existing_characters.add(row['character_name'])
        except FileNotFoundError:
            self.log(f"File not found: {csv_file_path}")
        except Exception as e:
            self.log(f"Error reading file {csv_file_path}: {e}")

    def parse(self, response):
        # Extract data from Main and Secondary Characters sections
        # Uses title of section as character name and paragraph below as role
        main_characters = response.xpath('//span[@id="Main_characters"]/ancestor::h2/following-sibling::h3')
        secondary_characters = response.xpath('//span[@id="Secondary_characters"]/ancestor::h2/following-sibling::h3')

        for characters in [main_characters, secondary_characters]:
            for character in characters:
                character_name = character.xpath('.//span[@class="mw-headline"]/text()').get().strip()
                role = character.xpath('./following-sibling::p[1]').xpath('string()').get().strip()

                if character_name and character_name not in self.existing_characters:
                    yield {
                        'character_name': character_name,
                        'role': role
                    }
                    self.existing_characters.add(character_name)

        # Extracts data from Recurring Characters table, only name and role.
        recurring_characters_table = response.xpath('//span[@id="Recurring_characters"]/following::table[contains(@class, "wikitable sortable collapsible")][1]')
        if recurring_characters_table:
            rows = recurring_characters_table.xpath('.//tr')[1:]  # Skip header row
            previous_role = ""  # To store the role of the previous character
            for row in rows:
                cells = row.xpath('.//td')
                if len(cells) >= 1:
                    character_names = cells[0].xpath('string()').get().strip().split(',')

                    # Try to get role, use previous role if not available, for cases where character has same role such Goth Kids.
                    if len(cells) >= 3:
                        current_role = cells[2].xpath('string()').get().strip()
                        if current_role:
                            previous_role = current_role

                    for character_name in character_names:
                        character_name = character_name.strip()
                        if character_name and character_name not in self.existing_characters:
                            yield {
                                'character_name': character_name,
                                'role': previous_role
                            }
                            self.existing_characters.add(character_name)
