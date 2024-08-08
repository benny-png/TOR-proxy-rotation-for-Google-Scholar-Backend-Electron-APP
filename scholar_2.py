import re
import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from tor_proxy import TorProxy  # Import the TorProxy class

class PaperScraper:
    def __init__(self):
        # Initialize the TorProxy
        self.proxy = TorProxy()
        self.proxy.start()

        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        # Add these lines to use your specific user profile
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--user-data-dir=C:\\Users\\User\\AppData\\Local\\Google\\Chrome\\User Data')
        options.add_argument('--profile-directory=Profile 9')
        options.add_argument('--headless')  

        # Set proxy for Chrome
        proxy_address = "socks5://localhost:9054"
        options.add_argument(f'--proxy-server={proxy_address}')
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def process_authors(self, match):
        first_group = match.group(1)[0]
        if match.group(3):
            second_group = match.group(2)[0]
            return f"{match.group(3)} {first_group}. {second_group}."
        else:
            return f"{match.group(2)} {first_group}."

    def scrape_paper_details(self, url):
        self.driver.get(url)
        time.sleep(1)

        details = {
            'authors': 'N/A',
            'journal': 'N/A',
            'volume': 'N/A',
            'pages': 'N/A',
            'booktitle': 'N/A',
            'organization': 'N/A'
        }

        # Authors
        try:
            authors_field = self.driver.find_element(By.XPATH, '//div[@class="gsc_oci_field" and contains(text(), "Authors")]')
            authors_value = authors_field.find_element(By.XPATH, './following-sibling::div[@class="gsc_oci_value"]')
            authors_text = authors_value.text
            details['authors'] = re.sub(r'(\w+)\s+(\w+)(?:\s+(\w+))?', self.process_authors, authors_text)
        except:
            try:
                authors_field = self.driver.find_element(By.XPATH, '//div[@class="gsc_oci_field" and contains(text(), "Inventors")]')
                authors_value = authors_field.find_element(By.XPATH, './following-sibling::div[@class="gsc_oci_value"]')
                authors_text = authors_value.text
                details['authors'] = re.sub(r'(\w+)\s+(\w+)(?:\s+(\w+))?', self.process_authors, authors_text)
            except:
                pass

        # Journal/Book/Source
        for field in ["Journal", "Book", "Source"]:
            try:
                journal_field = self.driver.find_element(By.XPATH, f'//div[@class="gsc_oci_field" and contains(text(), "{field}")]')
                journal_value = journal_field.find_element(By.XPATH, './following-sibling::div[@class="gsc_oci_value"]')
                details['journal'] = journal_value.text
                break
            except:
                pass

        # Volume
        try:
            volume_field = self.driver.find_element(By.XPATH, '//div[@class="gsc_oci_field" and contains(text(), "Volume")]')
            volume_value = volume_field.find_element(By.XPATH, './following-sibling::div[@class="gsc_oci_value"]')
            details['volume'] = volume_value.text
        except:
            pass

        # Pages
        try:
            pages_field = self.driver.find_element(By.XPATH, '//div[@class="gsc_oci_field" and contains(text(), "Pages")]')
            pages_value = pages_field.find_element(By.XPATH, './following-sibling::div[@class="gsc_oci_value"]')
            details['pages'] = pages_value.text
        except:
            pass

        # Booktitle (for conference papers)
        try:
            booktitle_field = self.driver.find_element(By.XPATH, '//div[@class="gsc_oci_field" and contains(text(), "Conference")]')
            booktitle_value = booktitle_field.find_element(By.XPATH, './following-sibling::div[@class="gsc_oci_value"]')
            details['booktitle'] = booktitle_value.text
        except:
            pass

        # Organization (for conference papers)
        try:
            org_field = self.driver.find_element(By.XPATH, '//div[@class="gsc_oci_field" and contains(text(), "Publisher")]')
            org_value = org_field.find_element(By.XPATH, './following-sibling::div[@class="gsc_oci_value"]')
            details['organization'] = org_value.text
        except:
            pass
 
        return details

    def parse_bibtex(self, bibtex_string):
        parsed = {}
        fields = ['title', 'author', 'booktitle', 'pages', 'year', 'organization']
        for field in fields:
            match = re.search(rf'{field}\s*=\s*{{(.*?)}}', bibtex_string)
            if match:
                parsed[field] = match.group(1)
            else:
                parsed[field] = 'N/A'
        return parsed

    def scrape_and_parse(self, input_file, output_file, renew_interval=5):
        with open(input_file, mode='r', encoding='utf-8') as file, \
             open(output_file, mode='w', newline='', encoding='utf-8') as csv_file:
            reader = csv.DictReader(file)
            fieldnames = ['NAME', 'AUTHORS', 'YEAR', 'TITLE', 'JOURNAL', 'VOLUME', 'PAGES', 'BOOKTITLE', 'ORGANIZATION']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            for count, row in enumerate(reader, start=1):
                link = row['LINK']
                name = row['NAME']
                title = row.get('TITLE', 'N/A')
                year = row.get('YEAR', 'N/A')
                print(f"Scraping: {name}")

                details = self.scrape_paper_details(link)

                writer.writerow({
                    'NAME': name,
                    'AUTHORS': details['authors'],
                    'YEAR': year,
                    'TITLE': title,
                    'JOURNAL': details['journal'],
                    'VOLUME': details['volume'],
                    'PAGES': details['pages'],
                    'BOOKTITLE': details['booktitle'],
                    'ORGANIZATION': details['organization']
                })

                # Renew Tor connection every `renew_interval` papers
                if count % renew_interval == 0:
                    print("Renewing Tor connection...")
                    self.proxy.renew_connection()
                    #time.sleep(10)  # Give Tor some time to establish a new connection

        print(f"SAVED TO {output_file}")

    def close(self):
        self.driver.quit()
        self.proxy.stop()  # Stop Tor when done

# Example usage:
# scraper = PaperScraper()
# scraper.scrape_and_parse('research_papers.csv', 'Research_paper_details.csv')
# scraper.close()
