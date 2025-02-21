from bs4 import BeautifulSoup, Tag
import requests

class NatureArticle:
    def scrape(site_link: str, default_voice="espvolt", tags=[]):
        req = requests.get(site_link)

        if (req.status_code != 200):
            return None
        
