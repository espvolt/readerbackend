from book import Book, Chapter, ChapterTextSection, output_book
from bs4 import Tag, BeautifulSoup
import requests

POSSIBLE_TITLE_LOCATIONS = ("mw-page-title-main", "mw-first-heading")
INVALID_CHAPTER_TITLES = ("see also", "references", "notes")

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

    def _convert_abbr(tag: Tag):
        for y in tag.find_all(name="abbr"):
            tag_: Tag = y
            tag_.string.replace_with(tag_["title"])

    def scrape(site_link: str, voice_clone: str="espvolt", additional_tags: list=[]):
        resp = requests.get(site_link)

        if (resp.status_code != 200):
            return None
        
        soup = BeautifulSoup(resp.content, "html.parser")

        # find title

        book_title: str | None = None

        for location in POSSIBLE_TITLE_LOCATIONS:
            _temp: list[Tag] = soup.find_all(class_=location)

            if (len(_temp) > 0):
                book_title = _temp[0].text

        if (book_title is None):
            book_title = site_link

        bodyContent = soup.find(class_="mw-content-ltr")

        chapters = []

        current_chapter = Chapter("Introduction", [])
        current_traversal = bodyContent.findChildren(recursive=False)
        current_text = ""
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
                Wikipedia._convert_abbr(tag)
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
                    
                    if ("mw-heading2" in tag["class"]): # Chapter Change
                        current_chapter.text_sections.append(ChapterTextSection(voice_clone, current_text))
                        chapters.append(current_chapter)
                        current_chapter = None
                        current_text = ""

                        if (tag.text.lower().strip() in INVALID_CHAPTER_TITLES):
                            traveral_finished = True
                            break
                        
                        current_chapter = Chapter(tag.text, [])

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

                if (tag.name == "blockquote" and "templatequote" in tag["class"]):
                    quote_tag = tag.findChild(class_="templatequotecite")
                    quote_text  = quote_tag.text
                    quote_tag.decompose()

                    clean_text = tag.text.strip()
                    
                    if (not clean_text.endswith(".")):
                        clean_text += "."

                    current_text += clean_text

                    clean_text = quote_text.strip()
                    if (clean_text.startswith("—")): # remove the dash from the quote text
                        clean_text = clean_text[1:].strip()

                    clean_text = "From " + clean_text

                    if (not clean_text.endswith(".")):
                        clean_text += "."

                    current_text += clean_text
                
                    continue
                    
                if (not clean_text.endswith(".")):
                    clean_text += ". "

                current_text += clean_text

        if (current_chapter is not None):
            current_chapter.text_sections.append(ChapterTextSection(voice_clone, current_text))
            chapters.append(current_chapter)
                
        return Book(book_title, voice_clone, ["wikipedia"] + additional_tags, chapters)    


if __name__ == "__main__":
    pass    