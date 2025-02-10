from bs4 import BeautifulSoup, Tag
import requests
from book import Book, Chapter
import re
# import book_tts

import logging
import http.client


# You must initialize logging, otherwise you'll not see debug output.
# http.client.HTTPConnection.debuglevel = 1
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True


class Wikipedia:
    def _decompose_references(tag: Tag):
        for y in tag.find_all(id=lambda attr: attr is not None and attr.startswith("cite_ref")):
            y.decompose()

    def _decompose_edit_section(tag: Tag):
        for y in tag.find_all(class_="mw-editsection"):
            y.decompose()

    def _decompose_citation(tag: Tag):
        for y in tag.find_all(title="Wikipedia:Citation needed"):
            tag_: Tag = y
            tag_.find_parent("sup").decompose()

    def scrape(site_link: str, voice_clone: str="espvolt", additional_tags: list=[]):
        resp = requests.get(site_link)

        if (resp.status_code != 200):
            return None
        
        soup = BeautifulSoup(resp.content, "html.parser")

        book_title = soup.find_all(class_="mw-page-title-main")[0].text
        bodyContent = soup.find(class_="mw-content-ltr")

        chapters = []

        current_chapter = Chapter("Introduction", "")    
        current_traversal = bodyContent.findChildren(recursive=False)

        traveral_finished = False

        while not traveral_finished:
            for x in current_traversal:
                tag: Tag = x
                
                if (tag is None):
                    print(current_traversal)
                    print("ERROR")
                    break
                    pass

                Wikipedia._decompose_references(tag)

                if (tag.name == "style" or tag.name == "figure"):
                    continue
                if (tag.name == "table" and tag["class"] is not None and "infobox" in tag["class"]):
                    continue

                if (tag.name == "meta"):
                    current_traversal = tag.findChildren(recursive=False)
                    break
                
                if (tag.name == "table" and tag["class"] is not None and "sidebar" in tag["class"]):
                    continue
                
                if (tag.findChild(title="Wikipedia:Citation needed")):
                    Wikipedia._decompose_citation(tag)
                
                if (tag.name == "div" and tag["class"] is not None and "mw-heading" in tag["class"]):
                    Wikipedia._decompose_edit_section(tag)
                    
                    if ("mw-heading2" in tag["class"]):
                        chapters.append(current_chapter)
                        current_chapter = None

                        if (tag.text.lower().strip() == "see also" or tag.text.lower().strip() == "references"):
                            traveral_finished = True
                            break
                        
                        current_chapter = Chapter(tag.text, "")

                if (tag.get("role") is not None and tag["role"] == "note"):
                    continue
                
                clean_text = tag.text.strip("\n")
                if (len(clean_text) == 0):
                    continue
            
                if (tag.name == "ol"):
                    clean_text = ""
                    index = 1

                    for x in tag.findChildren(recursive=False):
                        Wikipedia._decompose_references(x)
                        clean_text += str(index) + ", " + x.text + ". "
                        index += 1


                if (not clean_text.endswith(".")):
                    clean_text += ". "

                current_chapter.text += clean_text

        if ( current_chapter is not None):
            chapters.append(current_chapter)
                
        return Book(book_title, voice_clone, ["wikipedia"] + additional_tags, chapters)
    


if __name__ == "__main__":
    import book_tts
    book: Book = Wikipedia.scrape("https://en.wikipedia.org/wiki/Astral_projection")
    for chapter in book.chapters:
        with open(f"./test/{chapter.title}", "w", encoding="utf-8") as f:
            f.writelines(chapter.text.split("."))
