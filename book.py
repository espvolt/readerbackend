from dataclasses import dataclass

@dataclass
class Chapter:
    title: str
    text: str

    def __repr__(self):
        return "{" + self.title + f", ~{len(self.text)}" + "}"

@dataclass
class Book:
    title: str
    voice_clone: str
    tags: tuple[str] = ()
    chapters: tuple[Chapter] = ()