
import re
from io import open
from typing import Iterator

from .ggra_errors import GgraParserError
from .custom_token import Token

PATTERNS = {
    "comment":          r"//.*",
    "linebreak":        r"\n",
    "spaces":           r"[ ]+",

    # "float":            r"-?[0-9]+\.[0-9]+",
    # "integer":          r"-?[0-9]+",

    "identifier":       r"\b[A-Za-z_0-9]+\b",
    "string":           r"\"([^\\\"\n]|\\.)*\"",
    "epsilon":          r"<>",
    "nonterminal":      r"<[ ]*~?[ ]*[A-Za-z_0-9]+[ ]*>",
    #planned: <[ ]*~?[ ]*[A-Za-z_0-9]+[ ]*(#\d+)?[ ]*>
    #<[ ]*~[ ]*[A-Za-z_0-9]+[ ]*>

    "open_paren":       r"\(",
    "close_paren":      r"\)",
    "arrow_normal":     r"->",
    "arrow_double":     r"=>",
    "arrow_labeled":    r"==[ ]*[A-Za-z_]+[ ]*=>",
    "nequals":          r"!=",
    "equals":           r"=",
    "colon":            r":",
    "or":               r"\|",
    "question":         r"\?",

    "dot":              r"\.",
    "comma":            r","
}

COMP_PATTERNS = {key: re.compile(regex) for key, regex in PATTERNS.items()}

#=================================
debreaked  = lambda text: text.replace("\n", "↵")

def next_token(text: str) -> tuple[Token, int]:
    """returns token and its length, if found"""
    for patname, pattern in COMP_PATTERNS.items():
        mat = pattern.match(text)

        if mat is None:
            # If the pattern does not fit the start of the string
            continue

        content = mat.group()
        span    = mat.span()
        length  = span[1] - span[0]
        return Token(patname, content), length
    
    tek = debreaked(text)
    raise GgraParserError(
        "Lexer: Generating Tokens",
        ["No available token:", f"{tek[:min(16, len(tek))]} ...", "^"]
    )

def tokens(text: str, ignore_types: list[str]) -> Iterator[tuple[Token, int]]:
    """yields all tokens from the text; ignored if token type in ignore_types"""
    current_text = text
    while len(current_text) > 0:
        token, tokenlength = next_token(current_text)
        if token.name not in ignore_types:
            yield token, tokenlength
        current_text = current_text[tokenlength:]

def token_lines(text: str, ignore_types: list[str] = []) -> Iterator[list]:
    """Iterator. Returns tokens in the line"""
    token_stack     = []
    for token, _ in tokens(text+"\n", ignore_types):
        if token.name == "linebreak":
            yield token_stack
            token_stack = []
            continue
        token_stack.append(token)
    
#=================================
def write_token_file(token_stream, ignore_types: list[str], filename: str = "out_tokens.txt"):
    with open(filename, "w", encoding="utf-8") as doc:
        for token, _ in token_stream:
            if token.name in ignore_types:
                continue
            doc.write(f"{token}\n")
