from llvmlite import ir
from lexer import Lexer
from parser_simmer import Parser
from semantic import SemanticAnalyzer

class CodeGen:
    def __init__(self):
        self.module = ir.Module(name="simmer_module")
        self.builder = None
        self.func = None
        self.symbol_table = {}

    def generate(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"No codegen method defined for {type(node).__name__}")

    def visit_Program(self, node):
        i32 = ir.IntType(32)
        func_type = ir.FunctionType(i32, ())
        self.func = ir.Function(self.module, func_type, name="main")
        block = self.func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

        for stmt in node.statements:
            self.generate(stmt)

        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(i32, 0))

    def visit_Declaration(self, node):
        i32 = ir.IntType(32)
        ptr = self.builder.alloca(i32, name=node.name)
        self.symbol_table[node.name] = ptr
        value = self.generate(node.value)
        self.builder.store(value, ptr)

    def visit_Assignment(self, node):
        ptr = self.symbol_table[node.name]
        value = self.generate(node.value)
        self.builder.store(value, ptr)

    def visit_Return(self, node):
        value = self.generate(node.value)
        self.builder.ret(value)

    def visit_BinOp(self, node):
        left = self.generate(node.left)
        right = self.generate(node.right)
        if node.op == '+': return self.builder.add(left, right, name="addtmp")
        elif node.op == '-': return self.builder.sub(left, right, name="subtmp")
        elif node.op == '*': return self.builder.mul(left, right, name="multmp")
        elif node.op == '/': return self.builder.sdiv(left, right, name="divtmp")

    def visit_Number(self, node):
        return ir.Constant(ir.IntType(32), node.value)

    def visit_Identifier(self, node):
        ptr = self.symbol_table[node.name]
        return self.builder.load(ptr, name=node.name + "_val")

    def visit_Condition(self, node):
        left = self.generate(node.left)
        right = self.generate(node.right)
        op_map = {'==': '==', '<': '<', '>': '>', '<=': '<=', '>=': '>='}
        return self.builder.icmp_signed(op_map[node.op], left, right, name="condtmp")

    def visit_IfElse(self, node):
        cond_val = self.generate(node.condition)
        then_block = self.func.append_basic_block(name="then")
        else_block = self.func.append_basic_block(name="else")
        merge_block = self.func.append_basic_block(name="ifcont")
        
        self.builder.cbranch(cond_val, then_block, else_block)
        
        self.builder.position_at_end(then_block)
        for stmt in node.then_body: self.generate(stmt)
        if not self.builder.block.is_terminated: self.builder.branch(merge_block)
            
        self.builder.position_at_end(else_block)
        for stmt in node.else_body: self.generate(stmt)
        if not self.builder.block.is_terminated: self.builder.branch(merge_block)
            
        self.builder.position_at_end(merge_block)

    def visit_WhileLoop(self, node):
        loop_cond_block = self.func.append_basic_block(name="loopcond")
        loop_body_block = self.func.append_basic_block(name="loopbody")
        loop_end_block = self.func.append_basic_block(name="loopend")

        self.builder.branch(loop_cond_block)

        self.builder.position_at_end(loop_cond_block)
        cond_val = self.generate(node.condition)
        self.builder.cbranch(cond_val, loop_body_block, loop_end_block)

        self.builder.position_at_end(loop_body_block)
        for stmt in node.body:
            self.generate(stmt)
        
        if not self.builder.block.is_terminated:
            self.builder.branch(loop_cond_block)

        self.builder.position_at_end(loop_end_block)

# --- Test the Code Generator ---
if __name__ == "__main__":
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
    parser = Parser(lexer.tokenize(test_script))
    ast = parser.parse()
    
    SemanticAnalyzer().analyze(ast)
    
    codegen = CodeGen()
    codegen.generate(ast)
    print("\n--- GENERATED LLVM IR ---")
    print(codegen.module)