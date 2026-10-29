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
        self.printf_func = None       # External printf declaration
        self.printf_fmt_str = None     # Global "%d\n" format string

    def generate(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"No codegen method defined for {type(node).__name__}")

    def _declare_printf(self):
        """Declare the external C printf function and the global format string for integer printing."""
        if self.printf_func is None:
            # Declare: int printf(const char*, ...)
            voidptr_ty = ir.IntType(8).as_pointer()
            printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
            self.printf_func = ir.Function(self.module, printf_ty, name="printf")

            # Create global format string: "%d\n\0"
            fmt = "%d\n\0"
            fmt_bytes = bytearray(fmt.encode("utf8"))
            fmt_ty = ir.ArrayType(ir.IntType(8), len(fmt_bytes))
            global_fmt = ir.GlobalVariable(self.module, fmt_ty, name=".fmt_int")
            global_fmt.linkage = "private"
            global_fmt.global_constant = True
            global_fmt.initializer = ir.Constant(fmt_ty, [ir.Constant(ir.IntType(8), b) for b in fmt_bytes])
            self.printf_fmt_str = global_fmt

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
        # Modulo operator: signed remainder
        elif node.op == '%': return self.builder.srem(left, right, name="modtmp")

    def visit_Number(self, node):
        return ir.Constant(ir.IntType(32), node.value)

    def visit_Identifier(self, node):
        ptr = self.symbol_table[node.name]
        return self.builder.load(ptr, name=node.name + "_val")

    def visit_Condition(self, node):
        left = self.generate(node.left)
        right = self.generate(node.right)
        # Added '!=' for not-equal comparison support
        op_map = {'==': '==', '!=': '!=', '<': '<', '>': '>', '<=': '<=', '>=': '>='}
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

    # Print statement codegen: call printf with "%d\n" format string
    def visit_Print(self, node):
        self._declare_printf()
        value = self.generate(node.value)
        # Get a pointer to the first element of the format string
        zero = ir.Constant(ir.IntType(32), 0)
        fmt_ptr = self.builder.gep(self.printf_fmt_str, [zero, zero], name="fmt_ptr")
        self.builder.call(self.printf_func, [fmt_ptr, value])

    # For loop codegen: for <var> = <start> to <end> { <body> }
    # Implemented as: store start, branch to cond, compare var < end,
    # if true -> body (execute, increment by 1, branch to cond), else -> end
    def visit_ForLoop(self, node):
        i32 = ir.IntType(32)
        ptr = self.symbol_table[node.var_name]

        # Store the start value into the loop variable
        start_val = self.generate(node.start)
        self.builder.store(start_val, ptr)

        # Create basic blocks for the loop structure
        for_cond_block = self.func.append_basic_block(name="forcond")
        for_body_block = self.func.append_basic_block(name="forbody")
        for_end_block = self.func.append_basic_block(name="forend")

        # Branch to condition check
        self.builder.branch(for_cond_block)

        # Condition block: compare var < end
        self.builder.position_at_end(for_cond_block)
        cur_val = self.builder.load(ptr, name=node.var_name + "_cur")
        end_val = self.generate(node.end)
        cond = self.builder.icmp_signed('<', cur_val, end_val, name="forcond")
        self.builder.cbranch(cond, for_body_block, for_end_block)

        # Body block: execute body, increment loop variable, branch back to condition
        self.builder.position_at_end(for_body_block)
        for stmt in node.body:
            self.generate(stmt)

        if not self.builder.block.is_terminated:
            # Increment the loop variable by 1
            cur = self.builder.load(ptr, name=node.var_name + "_inc")
            incremented = self.builder.add(cur, ir.Constant(i32, 1), name="nextval")
            self.builder.store(incremented, ptr)
            self.builder.branch(for_cond_block)

        # Continue after loop
        self.builder.position_at_end(for_end_block)

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
