import re

class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value
    def __repr__(self):
        return f"Token({self.type}, '{self.value}')"

# We have removed all culinary themes and replaced them with standard systems keywords
# Added 'print' for print statement, 'for' and 'to' for for-loop support
KEYWORDS = {'let', 'return', 'if', 'else', 'while', 'print', 'for', 'to'}

class Lexer:
    def __init__(self):
        self.rules = [
            ('WHITESPACE', r'\s+'),
            # Single-line comments: // until end of line (skipped like whitespace)
            ('COMMENT', r'//[^\n]*'),
            ('NUMBER', r'\d+'),
            ('IDENTIFIER', r'[a-zA-Z_]\w*'),
            # Operator ordering: multi-char ops (!=, ==, <=, >=) before single-char; added % for modulo
            ('OPERATOR', r'==|!=|<=|>=|<|>|[+\-*/%=]'),
            # Punctuation: braces and parentheses for grouping
            ('PUNCTUATION', r'[{}()]')
        ]
        
    def tokenize(self, text):
        tokens = []
        pos = 0
        while pos < len(text):
            match = None
            for token_type, pattern in self.rules:
                regex = re.compile(pattern)
                match = regex.match(text, pos)
                if match:
                    value = match.group(0)
                    # Skip whitespace and comments (don't add to token list)
                    if token_type not in ('WHITESPACE', 'COMMENT'):
                        # Check if the identifier is actually one of our new keywords
                        if token_type == 'IDENTIFIER' and value in KEYWORDS:
                            tokens.append(Token('KEYWORD', value))
                        else:
                            tokens.append(Token(token_type, value))
                    pos = match.end(0)
                    break
            if not match:
                raise SyntaxError(f"Illegal character at position {pos}: {text[pos]}")
        return tokens
