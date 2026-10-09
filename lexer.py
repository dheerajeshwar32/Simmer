import re

class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value
    def __repr__(self):
        return f"Token({self.type}, '{self.value}')"

# We have removed all culinary themes and replaced them with standard systems keywords
KEYWORDS = {'let', 'return', 'if', 'else', 'while'}

class Lexer:
    def __init__(self):
        self.rules = [
            ('WHITESPACE', r'\s+'),
            ('NUMBER', r'\d+'),
            ('IDENTIFIER', r'[a-zA-Z_]\w*'),
            ('OPERATOR', r'==|<=|>=|<|>|[+\-*/=]'),
            ('PUNCTUATION', r'[{}]')
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
                    if token_type != 'WHITESPACE':
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