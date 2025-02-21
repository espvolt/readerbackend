from scrapers.wikipedia import Wikipedia
from scrapers.nature import NatureArticle
from book import output_book
from text_filter import replace_units

assert replace_units("100m ") == "100 meters "
assert replace_units("100m wide") == "100 meters wide"
assert replace_units("1m long") == "1 meter long"
assert replace_units("1rad ") == "1 radian "
assert replace_units("100 m ") == "100 meters "
assert replace_units("who 100 m ") == "who 100 meters "
assert replace_units("100m.") == "100 meters."
assert replace_units("many 36 rad/s") == "many 36 radians per second"
assert replace_units("many 36 rad / s") == "many 36 radians per second"
assert replace_units("many 36 rad     / s") == "many 36 radians per second"
assert replace_units("fucking A 100m/s") == "fucking A 100 meters per second"
assert replace_units("fucking A 100N*m") == "fucking A 100 newtons meter"
assert replace_units("fucking A 100 N * m") == "fucking A 100 newtons meter"

if __name__ == "__main__":
    output_book(Wikipedia.scrape("https://en.wikipedia.org/wiki/After_the_Deluge_(painting)"), "./test_books/wikipedia.txt")
