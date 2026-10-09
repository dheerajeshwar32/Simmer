from lexer import Lexer
from parser_simmer import Parser, Program, Declaration, Assignment, Return, BinOp, Number, Identifier, Condition, IfElse, WhileLoop

class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = set()

    def analyze(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"No semantic analysis method defined for {type(node).__name__}")

    def visit_Program(self, node):
        for stmt in node.statements:
            self.analyze(stmt)

    def visit_Declaration(self, node):
        if node.name in self.symbol_table:
            raise Exception(f"Semantic Error: Variable '{node.name}' is already declared.")
        self.symbol_table.add(node.name)
        self.analyze(node.value)

    def visit_Assignment(self, node):
        if node.name not in self.symbol_table:
            raise Exception(f"Semantic Error: Cannot assign to undeclared variable '{node.name}'.")
        self.analyze(node.value)

    def visit_Return(self, node):
        self.analyze(node.value)

    def visit_BinOp(self, node):
        self.analyze(node.left)
        self.analyze(node.right)

    def visit_Number(self, node): pass

    def visit_Identifier(self, node):
        if node.name not in self.symbol_table:
            raise Exception(f"Semantic Error: Using undeclared variable '{node.name}'.")

    def visit_Condition(self, node):
        self.analyze(node.left)
        self.analyze(node.right)

    def visit_IfElse(self, node):
        self.analyze(node.condition)
        for stmt in node.then_body: self.analyze(stmt)
        for stmt in node.else_body: self.analyze(stmt)
        
    def visit_WhileLoop(self, node):
        self.analyze(node.condition)
        for stmt in node.body:
            self.analyze(stmt)

# --- Test the Semantic Analyzer ---
if __name__ == "__main__":
    test_script = """
    let temp = 190
    let ready = 0
    if temp > 180 {
        ready = 1
    } else {
        ready = 0
    }
    return ready
    """
    lexer = Lexer()
    parser = Parser(lexer.tokenize(test_script))
    analyzer = SemanticAnalyzer()
    analyzer.analyze(parser.parse())
    print("Semantic Analysis passed! All variables are valid.")