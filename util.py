import os
import pathlib
import json
from bs4 import BeautifulSoup

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


