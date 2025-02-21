import re

INVALID_LONE_TOKENS = ("\n", " ", ".", "")
UNITS = {
    "m": "meter",
    "s": "second",
    "kg": "kilogram",
    "a": "amp",
    "k": "kelvin",
    "mol": "mole",
    "cd": "candela",
    "rad": "radian",
    "hz": "hertz",
    "n": "newton",
    "pa": "pascal",
    "j": "joule",
    "w": "watt",
    "c": "coulomb",
    "v": "volt"
}

RATE_CHARACTERS = {
    "\/": "per", # escaped "/"
    "\*": ("", False), 
    "⋅": ("", False) # this is a multiplication thing
}
def new_len(a, b):
    return len(a) + len(b)

def strip_lone_tokens(a: str) -> str:
    for token in INVALID_LONE_TOKENS:
        a = a.strip(token)

    return a

def split_text_token_limit(text: str, current_split_token=".", token_limit=150) -> list[str]:
    text_split_between_tokens = text.split(current_split_token)
    current_text = ""
    res = []
    
    for text in text_split_between_tokens:
        strip_lone_tokens(text)

        if (text in INVALID_LONE_TOKENS):
            continue
        
        if (new_len(current_text, text) > token_limit):
            if (current_text == ""):
                split_whitespace = split_text_token_limit(text, " ")
                res.extend(split_whitespace)
            else:
                res.append(current_text)
                current_text = text + current_split_token
        else:
            current_text += text + current_split_token

    if (current_text != ""):
        res.append(current_text)

    return res

def find_quantity_str(text: str, start_index: int) -> str:
    """
    finds quanity from the end of a number
    ex. 100m
          ^ start_index, returns "100"
    """

    i = start_index
    res = ""
    while ((text[i].isnumeric() or text[i] == ".") and i >= 0):
        res += text[i]
        i -= 1

    return res[::-1]

assert find_quantity_str("100m", 2) == "100"
assert find_quantity_str("start 3.14 is pi", 9) == "3.14"

def replace_units(text: str):
    _text = text.lower()
    

    

    for sym, unit in UNITS.items(): # first pass,
        for rate_char, rate_str in RATE_CHARACTERS.items():
            _rate_str = rate_str
            add_spaces = True
            if (isinstance(rate_str, tuple)):
                add_spaces = rate_str[1]
                _rate_str = rate_str[0]

                pass
            regex_str = rate_char + "\s*" + sym + "[\s\.]?"
            # print(regex_str)
            regex = re.compile(regex_str)
            while (match := regex.search(_text)) is not None:
                span = match.span()
                
                j = span[0] - 1
                
                if (text[j] == " "):
                    while (j >= 0 and text[j] == " "):
                        j -= 1

                    j += 1
                else:
                    j = span[0]

                # be = text[:j] + (" " if add_spaces else "") + _rate_str + " " + unit + text[span[1]:]
                text = text[:j] + (" " if add_spaces else "") + _rate_str + " " + unit + text[span[1]:]
                _text = text.lower()

    for sym, unit in UNITS.items():
        plural = True
        _unit = unit

        if (isinstance(unit, tuple)):
            plural = unit[1]
            _unit = unit[0]
        
        regex = re.compile("\d\s*" + sym + "[\s\.]")

        while (match := regex.search(_text)) is not None:
            # find quanitity
            span = match.span()
            i = span[0]

            add_s = False

            num = find_quantity_str(text, i)

            if (abs(float(num)) > 1):
                add_s = True
            
            end_char = text[span[1] - 1]
            text = text[:span[0] + 1] + " " + _unit + ("s" if add_s and plural else "") + end_char + text[span[1]:]
            _text = text.lower()

    return text

def filter_seq(text: str, token_limit=150):
    return split_text_token_limit(text, token_limit=token_limit)
