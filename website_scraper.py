import requests
from bs4 import BeautifulSoup
import re
from pprint import pprint

def split_text_to_tokens(text: str) -> list[str]:
    res: list[str] = []
    start = 0

    for i, char in enumerate(text):
        if (char in ("!", ".", "?", "\n")):
            if (char == "\n" and text[i - 1] != "."):
                res.append(text[start: i + 1] + ". ")
            else:
                res.append(text[start: i + 1])


            start = i + 1

    res.append(text[start: len(text) + 1])
    
    i = 0

    while i < len(res):
        current = res[i]
        if (len(current) > 250):
            j = len(current) - 1

            while j >= 0:
                if (current[j] == " "):
                    if (len(current[0: j]) < 250):
                        res[i] = current[0: j]
                        res.insert(i + 1, current[j: len(current)])
                        break
                j -= 1    

        i += 1            

    i = 0

    while i < len(res):
        if (res[i] in ("[]\n", "\n", "", "\"\n")):
            res.pop(i)
            continue

        if (i != 0 and len(res[i - 1] + res[i]) < 250):
            res[i - 1] = res[i - 1] + res[i]
            res.pop(i)
            continue
        
        res[i] = res[i].strip()
        i += 1

    
    print(res)
    return res


        
class SiteFilter:
    def __init__(self):
        self.id_dict: dict[str, list[str]] = {
            "startswith": [],
            "stopon": []
        }

        self.class_dict: dict[str, list[str]] = {
            "is": []
        }

        self.title_dict: dict[str, list[str]] = {
            "is": []
        }

    def id_starts_with(self, *args: list[str]) -> "SiteFilter":
        self.id_dict["startswith"].extend(args)
        return self
    
    def class_is(self, *args: list[str]) -> "SiteFilter":
        self.class_dict["is"].extend(args)
        return self
    
    def title_is(self, *args: list[str]) -> "SiteFilter":
        self.title_dict["is"].extend(args)
        return self
    

    def _get_kwargs(self):
        def id_check(x: str):
            if x is None:
                return False

            for i in self.id_dict["startswith"]:
                if (x.startswith(i)):
                    return True
                                    
            return False
        
        def class_check(x: str):
            if (x is None):
                return False

            for i in self.class_dict["is"]:
                if (x == i):
                    return True
                
            return False
        
        def title_check(x: str):
            if (x is None):
                return False
            
            for i in self.title_dict["is"]:
                if (x == i):
                    return True
                
            return False
        
        return {"id": id_check, "class": class_check, "title": title_check}
    
    def filter_soup(self, soup: BeautifulSoup) -> None:
        kwargs = self._get_kwargs()
        for type in kwargs:
            for tag in soup(**{type: kwargs[type]}):
                tag.decompose()

def wikipedia(extension: str, cleanup=True, output_file: str | None=None) -> str | None:
    r = requests.get(f"https://en.wikipedia.org/wiki/{extension}")
    if (r.status_code == 200):
        soup = BeautifulSoup(r.content, "html.parser")
        # print(soup.get_text())
        main_content = soup.select_one("#mw-content-text")

        if (cleanup):
            SiteFilter().id_starts_with("cite") \
                .class_is("mw-editsection") \
                .title_is("Wikipedia:Citation needed") \
                .filter_soup(main_content)

            parent = main_content.find("h2", {"id": "See_also"}).parent

            for tag in parent.find_all_next():
                if (tag.id is not None and tag.id == "bodyContent"):
                    break

                tag.decompose()
        if (output_file != None):
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(main_content.get_text())

        return main_content.get_text()

if (__name__ == "__main__"):
    split_text_to_tokens(str(wikipedia("Lucid_Dream", output_file="./output/out.txt")))
