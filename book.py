from dataclasses import dataclass

@dataclass
class Chapter:
    title: str
    text: str

@dataclass
class Book:
    title: str
    voice_clone: str
    tags: tuple[str] = ()
    chapters: tuple[Chapter] = ()