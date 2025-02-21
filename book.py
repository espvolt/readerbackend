from dataclasses import dataclass
from text_filter import filter_seq

@dataclass
class Chapter:
    title: str
    text_sections: list["ChapterTextSection"]

    def __repr__(self):
        return "{" + self.title + f", ~{len(self.text)}" + "}"
@dataclass
class ChapterTextSection:
    reader: str
    text: str
    additional_parameters: dict | None = None
        
@dataclass
class Book:
    title: str
    voice_clone: str
    tags: tuple[str] = ()
    chapters: tuple[Chapter] = ()

def output_book(book: Book, outfile):
    current_level = 0
    with open(outfile, "w", encoding="utf-8") as f:
        f.writelines([
            "Book Title: " + book.title + "\n",
            "Chapters: \n"])
        
        current_level = 1
        
        for chapter in book.chapters:
            f.write("\t" * current_level + "Chapter Title: " + chapter.title + "\n")
            current_level += 1
            for section in chapter.text_sections:
                reader, text = section.reader, section.text

                f.write("\t" * current_level + "Current Reader: " + reader + "\n")
                current_level += 2
                split = filter_seq(text)

                for text in split:
                    f.write("\t" * current_level + text + "\n")

                f.write("\n")
                current_level -= 2

            f.write("\n")
            current_level -= 1
