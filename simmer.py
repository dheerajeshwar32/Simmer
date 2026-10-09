import sys
import os
import contextlib
import io
import ctypes
from llvmlite import binding as llvm

from lexer import Lexer
from parser_simmer import Parser
from semantic import SemanticAnalyzer
from codegen import CodeGen

def main():
    if len(sys.argv) < 2:
        print("Usage: python simmer.py <source_file.sim>")
        sys.exit(1)
        
    source_file = sys.argv[1]
    if not os.path.exists(source_file):
        print(f"Error: File '{source_file}' not found.")
        sys.exit(1)
        
    with open(source_file, 'r') as f:
        source_code = f.read()
        
    print(f"--- Compiling {source_file} ---")
    
    # 1. Frontend: Lexing, Parsing, Semantic Analysis
    lexer = Lexer()
    parser = Parser(lexer.tokenize(source_code))
    ast = parser.parse()
    
    with contextlib.redirect_stdout(io.StringIO()):
        SemanticAnalyzer().analyze(ast)
        
    # 2. Backend: Code Generation
    codegen = CodeGen()
    codegen.generate(ast)
    raw_ir = str(codegen.module)
    
    # 3. LLVM Initialization
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    
    parsed_module = llvm.parse_assembly(raw_ir)
    parsed_module.verify()
    
    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    
    # 4. Optimizer Pipeline (PassBuilder)
    pto = llvm.create_pipeline_tuning_options(speed_level=3)
    pass_builder = llvm.create_pass_builder(target_machine, pto)
    pass_manager = pass_builder.getModulePassManager()
    
    pass_manager.run(parsed_module, pass_builder)
    optimized_ir = str(parsed_module)
    
    # Calculate performance metrics for the Review 2 requirement
    before_lines = len([line for line in raw_ir.split('\n') if '=' in line or 'ret' in line])
    after_lines = len([line for line in optimized_ir.split('\n') if '=' in line or 'ret' in line])
    
    print("\n--- OPTIMIZATION METRICS ---")
    print(f"Instructions before: {before_lines}")
    print(f"Instructions after:  {after_lines}")
    print(f"Efficiency Gain:     {before_lines - after_lines} redundant instructions eliminated!")
    
    # 5. JIT Execution
    print("\n--- JIT EXECUTION ---")
    engine = llvm.create_mcjit_compiler(parsed_module, target_machine)
    engine.finalize_object()
    engine.run_static_constructors()
    
    func_ptr = engine.get_function_address("main")
    cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(func_ptr)
    result = cfunc()
    
    print(f"Program exited with code: {result}")
    
    # 6. Object / Assembly Emission
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    asm_file = f"{base_name}.s"
    obj_file = f"{base_name}.o"
    
    print("\n--- DISK EMISSION ---")
    asm_code = target_machine.emit_assembly(parsed_module)
    with open(asm_file, "w") as f:
        f.write(asm_code)
    print(f"-> Saved native assembly to '{asm_file}'")
    
    obj_code = target_machine.emit_object(parsed_module)
    with open(obj_file, "wb") as f:
        f.write(obj_code)
    print(f"-> Saved machine object code to '{obj_file}'")
    
    print("\nCOMPILER PIPELINE COMPLETE.")

if __name__ == "__main__":
    main()

