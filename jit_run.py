from llvmlite import binding as llvm
import ctypes
from lexer import Lexer
from parser_simmer import Parser
from semantic import SemanticAnalyzer
from codegen import CodeGen
import contextlib
import io

# 1. Initialize
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

# 2. Our Standard Execution Script
test_script = """
let volume = 100
let time = 0

while volume > 50 {
    volume = volume - 10
    time = time + 1
}

return time
"""

# 3. Full Compilation Pipeline
lexer = Lexer()
parser = Parser(lexer.tokenize(test_script))
ast = parser.parse()

with contextlib.redirect_stdout(io.StringIO()):
    SemanticAnalyzer().analyze(ast)

codegen = CodeGen()
codegen.generate(ast)

# 4. Optimize
parsed_module = llvm.parse_assembly(str(codegen.module))
parsed_module.verify()
target = llvm.Target.from_default_triple()
target_machine = target.create_target_machine()
pto = llvm.create_pipeline_tuning_options(speed_level=3)
pass_builder = llvm.create_pass_builder(target_machine, pto)
pass_manager = pass_builder.getModulePassManager()
pass_manager.run(parsed_module, pass_builder)

# 5. JIT Execution
print("--- 1. JIT EXECUTION ---")
engine = llvm.create_mcjit_compiler(parsed_module, target_machine)
engine.finalize_object()
engine.run_static_constructors()

func_ptr = engine.get_function_address("main")
cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(func_ptr)
result = cfunc()

print(f"SUCCESS! The compiled script executed.")
print(f"Final returned value (Expected 5): {result}\n")

# 6. Disk Emission
print("--- 2. DISK EMISSION (Module 6 Requirement) ---")
asm_code = target_machine.emit_assembly(parsed_module)
with open("simmer_module.s", "w") as f:
    f.write(asm_code)
print("-> Saved native assembly to 'simmer_module.s'")

obj_code = target_machine.emit_object(parsed_module)
with open("simmer_module.o", "wb") as f:
    f.write(obj_code)
print("-> Saved machine object code to 'simmer_module.o'")
print("\nCOMPILER PIPELINE COMPLETE.")