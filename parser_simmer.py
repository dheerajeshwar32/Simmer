from lexer import Lexer

# --- 1. AST Nodes ---
class Program:
    def __init__(self, statements): self.statements = statements
    def __repr__(self): return f"Program({self.statements})"

class Declaration:
    def __init__(self, name, value): self.name, self.value = name, value
    def __repr__(self): return f"Decl({self.name}, {self.value})"

class Assignment:
    def __init__(self, name, value): self.name, self.value = name, value
    def __repr__(self): return f"Assign({self.name}, {self.value})"

class Return:
    def __init__(self, value): self.value = value
    def __repr__(self): return f"Return({self.value})"

class BinOp:
    def __init__(self, left, op, right): self.left, self.op, self.right = left, op, right
    def __repr__(self): return f"BinOp({self.left} {self.op} {self.right})"

class Number:
    def __init__(self, value): self.value = int(value)
    def __repr__(self): return f"Num({self.value})"

class Identifier:
    def __init__(self, name): self.name = name
    def __repr__(self): return f"Id({self.name})"

class Condition:
    def __init__(self, left, op, right): self.left, self.op, self.right = left, op, right
    def __repr__(self): return f"Cond({self.left} {self.op} {self.right})"

class IfElse:
    def __init__(self, condition, then_body, else_body): 
        self.condition, self.then_body, self.else_body = condition, then_body, else_body
    def __repr__(self): return f"If({self.condition}) Then({self.then_body}) Else({self.else_body})"

class WhileLoop:
    def __init__(self, condition, body):
        self.condition, self.body = condition, body
    def __repr__(self): return f"While({self.condition}) Body({self.body})"

# --- 2. The Parser ---
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected_type, expected_value=None):
        token = self.current()
        if token and token.type == expected_type and (expected_value is None or token.value == expected_value):
            self.pos += 1
            return token
        raise SyntaxError(f"Expected {expected_type} '{expected_value or ''}', got {token}")

    def parse(self):
        statements = []
        while self.current() is not None:
            statements.append(self.parse_statement())
        return Program(statements)

    def parse_statement(self):
        token = self.current()
        
        # Parse: let <name> = <expr>
        if token.type == 'KEYWORD' and token.value == 'let':
            self.consume('KEYWORD', 'let')
            name = self.consume('IDENTIFIER').value
            self.consume('OPERATOR', '=')
            value = self.parse_expression()
            return Declaration(name, value)
            
        # Parse: return <expr>
        elif token.type == 'KEYWORD' and token.value == 'return':
            self.consume('KEYWORD', 'return')
            value = self.parse_expression()
            return Return(value)
            
        # Parse: if <cond> { ... } else { ... }
        elif token.type == 'KEYWORD' and token.value == 'if':
            self.consume('KEYWORD', 'if')
            
            left_cond = self.parse_expression()
            cond_op = self.consume('OPERATOR').value
            right_cond = self.parse_expression()
            condition = Condition(left_cond, cond_op, right_cond)
            
            self.consume('PUNCTUATION', '{')
            then_body = []
            while self.current() and not (self.current().type == 'PUNCTUATION' and self.current().value == '}'):
                then_body.append(self.parse_statement())
            self.consume('PUNCTUATION', '}')
            
            else_body = []
            if self.current() and self.current().type == 'KEYWORD' and self.current().value == 'else':
                self.consume('KEYWORD', 'else')
                self.consume('PUNCTUATION', '{')
                while self.current() and not (self.current().type == 'PUNCTUATION' and self.current().value == '}'):
                    else_body.append(self.parse_statement())
                self.consume('PUNCTUATION', '}')
                
            return IfElse(condition, then_body, else_body)

        # Parse: while <cond> { ... }
        elif token.type == 'KEYWORD' and token.value == 'while':
            self.consume('KEYWORD', 'while')
            
            left_cond = self.parse_expression()
            cond_op = self.consume('OPERATOR').value
            right_cond = self.parse_expression()
            condition = Condition(left_cond, cond_op, right_cond)
            
            self.consume('PUNCTUATION', '{')
            body = []
            while self.current() and not (self.current().type == 'PUNCTUATION' and self.current().value == '}'):
                body.append(self.parse_statement())
            self.consume('PUNCTUATION', '}')
            return WhileLoop(condition, body)

        # Parse: <name> = <expr> (Assignment)
        elif token.type == 'IDENTIFIER':
            name = self.consume('IDENTIFIER').value
            self.consume('OPERATOR', '=')
            value = self.parse_expression()
            return Assignment(name, value)
            
        raise SyntaxError(f"Unexpected token in statement: {token}")

    def parse_expression(self):
        left = self.parse_term()
        while self.current() and self.current().type == 'OPERATOR' and self.current().value in ('+', '-'):
            op = self.consume('OPERATOR').value
            right = self.parse_term()
            left = BinOp(left, op, right)
        return left

    def parse_term(self):
        left = self.parse_primary()
        while self.current() and self.current().type == 'OPERATOR' and self.current().value in ('*', '/'):
            op = self.consume('OPERATOR').value
            right = self.parse_primary()
            left = BinOp(left, op, right)
        return left

    def parse_primary(self):
        token = self.current()
        if token.type == 'NUMBER':
            self.consume('NUMBER')
            return Number(token.value)
        elif token.type == 'IDENTIFIER':
            self.consume('IDENTIFIER')
            return Identifier(token.value)
        raise SyntaxError(f"Expected Number or Identifier, got {token}")

# --- Test the Parser ---
if __name__ == "__main__":
    # Test with standard programming syntax
    test_script = """
    let volume = 100
    let time = 0

    while volume > 50 {
        volume = volume - 10
        time = time + 1
    }

    return time
    """
    
    lexer = Lexer()
    tokens = lexer.tokenize(test_script)
    parser = Parser(tokens)
    ast = parser.parse()
    
    for stmt in ast.statements:
        print(stmt)