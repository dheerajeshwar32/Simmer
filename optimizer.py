from llvmlite import binding as llvm
from lexer import Lexer
from parser_simmer import Parser
from semantic import SemanticAnalyzer
from codegen import CodeGen
import contextlib
import io

# 1. Initialize the LLVM backend
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

# 2. Compile the script down to raw IR
test_script = """
let flour = 50
let butter = 50
let roux = flour + butter
return roux
"""

lexer = Lexer()
parser = Parser(lexer.tokenize(test_script))
ast = parser.parse()

# Suppress the semantic analyzer's print statement to keep output clean
with contextlib.redirect_stdout(io.StringIO()):
    SemanticAnalyzer().analyze(ast)

codegen = CodeGen()
codegen.generate(ast)
raw_ir = str(codegen.module)

print("--- BEFORE OPTIMIZATION (Module 4) ---")
print(raw_ir)

# 3. Parse the IR into the LLVM Execution Engine
parsed_module = llvm.parse_assembly(raw_ir)
parsed_module.verify()

# 4. Set up the Optimization Pass Manager (Modern API)
target = llvm.Target.from_default_triple()
target_machine = target.create_target_machine()

pto = llvm.create_pipeline_tuning_options(speed_level=3)
pass_builder = llvm.create_pass_builder(target_machine, pto)
pass_manager = pass_builder.getModulePassManager()

# 5. Run the optimizations!
pass_manager.run(parsed_module, pass_builder)

optimized_ir = str(parsed_module)
print("\n--- AFTER OPTIMIZATION (Module 5) ---")
print(optimized_ir)

# 6. Calculate Metrics for your Professor
# We count lines containing an assignment '=' or a 'ret' to estimate active instructions
before_lines = len([line for line in raw_ir.split('\n') if '=' in line or 'ret' in line])
after_lines = len([line for line in optimized_ir.split('\n') if '=' in line or 'ret' in line])

print("\n--- PERFORMANCE METRICS ---")
print(f"Instructions before: {before_lines}")
print(f"Instructions after:  {after_lines}")
print(f"Efficiency Gain:     {before_lines - after_lines} redundant instructions eliminated!")