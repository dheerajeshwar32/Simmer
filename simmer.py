#!/usr/bin/env python3
"""
Simmer Compiler — Main CLI Driver
==================================
Compiles .sim source files through the full pipeline:
  Source → Lexer → Parser → Semantic Analysis → LLVM IR → Optimizer → JIT / AOT

Usage:
    python simmer.py <source_file.sim>              # Full pipeline (default)
    python simmer.py <source_file.sim> --tokens      # Show lexer tokens
    python simmer.py <source_file.sim> --ast          # Show parsed AST
    python simmer.py <source_file.sim> --ir           # Show LLVM IR (before & after optimization)
    python simmer.py <source_file.sim> --no-opt       # Skip optimization
    python simmer.py <source_file.sim> --no-jit       # Skip JIT execution
    python simmer.py <source_file.sim> --verbose      # Show all intermediate stages

Authors: N. Dheeraj Eshwar & G. Surya Prakash
Course:  BCSE307P — Compiler Design Lab
"""

import sys
import os

# Auto-link venv packages if run via global python
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_venv_site = os.path.join(_BASE_DIR, "venv", "Lib", "site-packages")
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

import contextlib
import io
import ctypes
import argparse
from llvmlite import binding as llvm

from lexer import Lexer
from parser_simmer import Parser
from semantic import SemanticAnalyzer
from codegen import CodeGen

# ──────────────────────────────────────────────
#  ANSI Color Helpers (works on Windows 10+)
# ──────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
os.system('')  # Enable ANSI escape codes on Windows

class Color:
    BOLD    = '\033[1m'
    GREEN   = '\033[92m'
    CYAN    = '\033[96m'
    YELLOW  = '\033[93m'
    RED     = '\033[91m'
    MAGENTA = '\033[95m'
    DIM     = '\033[2m'
    RESET   = '\033[0m'

def header(text):
    """Print a section header with color."""
    print(f"\n{Color.CYAN}{Color.BOLD}{'─' * 50}")
    print(f"  {text}")
    print(f"{'─' * 50}{Color.RESET}")

def success(text):
    print(f"  {Color.GREEN}✓ {text}{Color.RESET}")

def info(text):
    print(f"  {Color.DIM}{text}{Color.RESET}")

def metric(label, value):
    print(f"  {Color.YELLOW}{label}: {Color.RESET}{value}")

# ──────────────────────────────────────────────
#  Main Compiler Pipeline
# ──────────────────────────────────────────────
def compile_source(source_code, source_file="<stdin>", args=None):
    """
    Run the full Simmer compilation pipeline on source_code.
    Returns a dict with compilation results and artifacts.
    """
    show_tokens = args and args.tokens
    show_ast    = args and args.ast
    show_ir     = args and args.ir
    verbose     = args and args.verbose
    skip_opt    = args and args.no_opt
    skip_jit    = args and args.no_jit

    results = {}

    # ── Phase 1: Lexical Analysis ──
    header("PHASE 1 — LEXICAL ANALYSIS")
    lexer = Lexer()
    tokens = lexer.tokenize(source_code)
    success(f"Tokenized: {len(tokens)} tokens produced")

    if show_tokens or verbose:
        print()
        for i, tok in enumerate(tokens):
            print(f"    [{i:3d}] {tok}")
    
    results['token_count'] = len(tokens)

    # ── Phase 2: Parsing (AST Construction) ──
    header("PHASE 2 — PARSING (AST CONSTRUCTION)")
    parser = Parser(tokens)
    ast = parser.parse()
    success(f"Parsed: {len(ast.statements)} top-level statements")

    if show_ast or verbose:
        print()
        for stmt in ast.statements:
            print(f"    {stmt}")

    results['statement_count'] = len(ast.statements)

    # ── Phase 3: Semantic Analysis ──
    header("PHASE 3 — SEMANTIC ANALYSIS")
    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)
    success(f"All variables valid. Symbol table: {analyzer.symbol_table}")

    results['symbols'] = list(analyzer.symbol_table)

    # ── Phase 4: LLVM IR Code Generation ──
    header("PHASE 4 — LLVM IR CODE GENERATION")
    codegen = CodeGen()
    codegen.generate(ast)
    raw_ir = str(codegen.module)
    success("LLVM IR generated successfully")

    if show_ir or verbose:
        print(f"\n{Color.DIM}{raw_ir}{Color.RESET}")

    results['raw_ir'] = raw_ir

    # ── Phase 5: LLVM Initialization & Optimization ──
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    parsed_module = llvm.parse_assembly(raw_ir)
    parsed_module.verify()

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()

    if not skip_opt:
        header("PHASE 5 — OPTIMIZATION (LLVM PassBuilder -O3)")
        pto = llvm.create_pipeline_tuning_options(speed_level=3)
        pass_builder = llvm.create_pass_builder(target_machine, pto)
        pass_manager = pass_builder.getModulePassManager()
        pass_manager.run(parsed_module, pass_builder)

        optimized_ir = str(parsed_module)

        # Calculate instruction metrics
        before = len([l for l in raw_ir.split('\n') if '=' in l or 'ret' in l])
        after  = len([l for l in optimized_ir.split('\n') if '=' in l or 'ret' in l])
        eliminated = before - after
        pct = (eliminated / before * 100) if before > 0 else 0

        metric("Instructions before optimization", before)
        metric("Instructions after optimization ", after)
        metric("Redundant instructions eliminated", f"{eliminated} ({pct:.1f}% reduction)")

        if show_ir or verbose:
            print(f"\n{Color.DIM}{optimized_ir}{Color.RESET}")

        results['instr_before'] = before
        results['instr_after'] = after
        results['optimized_ir'] = optimized_ir
    else:
        info("Optimization skipped (--no-opt)")
        results['instr_before'] = None
        results['instr_after'] = None

    # ── Phase 6: JIT Execution ──
    if not skip_jit:
        header("PHASE 6 — JIT EXECUTION")
        engine = llvm.create_mcjit_compiler(parsed_module, target_machine)
        engine.finalize_object()
        engine.run_static_constructors()

        func_ptr = engine.get_function_address("main")
        cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(func_ptr)

        # Capture stdout from the JIT (for print statements)
        jit_result = cfunc()

        success(f"Program exited with code: {Color.BOLD}{jit_result}{Color.RESET}")

        results['jit_result'] = jit_result
    else:
        info("JIT execution skipped (--no-jit)")
        results['jit_result'] = None

    # ── Phase 7: Native Code Emission ──
    header("PHASE 7 — NATIVE CODE EMISSION")

    base_name = os.path.splitext(os.path.basename(source_file))[0]
    output_dir = os.path.join(os.path.dirname(source_file) or '.', 'output')
    os.makedirs(output_dir, exist_ok=True)

    asm_file = os.path.join(output_dir, f"{base_name}.s")
    obj_file = os.path.join(output_dir, f"{base_name}.o")

    asm_code = target_machine.emit_assembly(parsed_module)
    with open(asm_file, "w") as f:
        f.write(asm_code)
    success(f"Saved native assembly  → {asm_file}")

    obj_code = target_machine.emit_object(parsed_module)
    with open(obj_file, "wb") as f:
        f.write(obj_code)
    success(f"Saved machine object   → {obj_file}")

    results['asm_file'] = asm_file
    results['obj_file'] = obj_file

    # ── Done ──
    print(f"\n{Color.GREEN}{Color.BOLD}{'═' * 50}")
    print(f"  SIMMER COMPILATION COMPLETE ✓")
    print(f"{'═' * 50}{Color.RESET}\n")

    return results

# ──────────────────────────────────────────────
#  CLI Entry Point
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog='simmer',
        description='🍲 Simmer Compiler — Compile .sim scripts to native machine code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python simmer.py script.sim              # Compile & run\n"
               "  python simmer.py script.sim --verbose     # Show all stages\n"
               "  python simmer.py script.sim --tokens      # Show lexer output\n"
               "  python simmer.py script.sim --ast --ir    # Show AST and IR\n"
    )
    parser.add_argument('source_file', help='Path to a .sim source file')
    parser.add_argument('--tokens', action='store_true', help='Display lexer tokens')
    parser.add_argument('--ast', action='store_true', help='Display parsed AST')
    parser.add_argument('--ir', action='store_true', help='Display LLVM IR (before & after optimization)')
    parser.add_argument('--no-opt', action='store_true', help='Skip the optimization pass')
    parser.add_argument('--no-jit', action='store_true', help='Skip JIT execution (only emit files)')
    parser.add_argument('--verbose', action='store_true', help='Show all intermediate representations')

    args = parser.parse_args()

    source_file = args.source_file
    if not os.path.exists(source_file):
        print(f"{Color.RED}Error: File '{source_file}' not found.{Color.RESET}")
        sys.exit(1)

    with open(source_file, 'r') as f:
        source_code = f.read()

    # Print banner
    print(f"\n{Color.MAGENTA}{Color.BOLD}")
    print("  ╔═══════════════════════════════════════════╗")
    print("  ║        🍲  SIMMER COMPILER  🍲           ║")
    print("  ║   Custom DSL → LLVM → Native Machine     ║")
    print("  ╚═══════════════════════════════════════════╝")
    print(f"{Color.RESET}")
    print(f"  {Color.DIM}Compiling: {source_file}{Color.RESET}")

    try:
        compile_source(source_code, source_file, args)
    except SyntaxError as e:
        print(f"\n{Color.RED}{Color.BOLD}  ✗ Syntax Error: {e}{Color.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Color.RED}{Color.BOLD}  ✗ Compilation Error: {e}{Color.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
