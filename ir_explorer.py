#!/usr/bin/env python3
"""
Simmer IR Explorer — Interactive LLVM IR visualization tool.
Shows the raw IR and optimized IR side-by-side with metrics.

Usage: python ir_explorer.py <source_file.sim>
       python ir_explorer.py              # Uses built-in demo
"""

import sys
import os
import contextlib
import io

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llvmlite import binding as llvm
from lexer import Lexer
from parser_simmer import Parser
from semantic import SemanticAnalyzer
from codegen import CodeGen

os.system('')

# Colors
BOLD    = '\033[1m'
RED     = '\033[91m'
GREEN   = '\033[92m'
CYAN    = '\033[96m'
YELLOW  = '\033[93m'
MAGENTA = '\033[95m'
DIM     = '\033[2m'
RESET   = '\033[0m'


def explore_ir(source_code, title="Simmer Script"):
    """Show raw IR, optimized IR, and assembly side-by-side with metrics."""

    # Frontend
    lexer = Lexer()
    tokens = lexer.tokenize(source_code)
    parser = Parser(tokens)
    ast = parser.parse()
    SemanticAnalyzer().analyze(ast)

    # Code Generation
    codegen = CodeGen()
    codegen.generate(ast)
    raw_ir = str(codegen.module)

    # LLVM Init
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    parsed_module = llvm.parse_assembly(raw_ir)
    parsed_module.verify()

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()

    # Optimize
    pto = llvm.create_pipeline_tuning_options(speed_level=3)
    pass_builder = llvm.create_pass_builder(target_machine, pto)
    pass_manager = pass_builder.getModulePassManager()
    pass_manager.run(parsed_module, pass_builder)

    optimized_ir = str(parsed_module)

    # Assembly
    asm_code = target_machine.emit_assembly(parsed_module)

    # Metrics
    before = len([l for l in raw_ir.split('\n') if '=' in l or 'ret' in l])
    after  = len([l for l in optimized_ir.split('\n') if '=' in l or 'ret' in l])
    eliminated = before - after
    pct = (eliminated / before * 100) if before > 0 else 0

    raw_lines = len([l for l in raw_ir.strip().split('\n') if l.strip()])
    opt_lines = len([l for l in optimized_ir.strip().split('\n') if l.strip()])
    asm_lines = len([l for l in asm_code.strip().split('\n') if l.strip()])

    # ── Display ──
    print(f"\n{MAGENTA}{BOLD}{'═' * 60}")
    print(f"  SIMMER IR EXPLORER — {title}")
    print(f"{'═' * 60}{RESET}")

    # Source Code
    print(f"\n{CYAN}{BOLD}┌─ SOURCE CODE ─────────────────────────────────────────┐{RESET}")
    for line in source_code.strip().split('\n'):
        print(f"  {line}")
    print(f"{CYAN}{BOLD}└───────────────────────────────────────────────────────┘{RESET}")

    # Raw IR
    print(f"\n{YELLOW}{BOLD}┌─ RAW LLVM IR ({raw_lines} lines) ───────────────────────────┐{RESET}")
    print(f"{DIM}{raw_ir}{RESET}")
    print(f"{YELLOW}{BOLD}└───────────────────────────────────────────────────────┘{RESET}")

    # Optimized IR
    print(f"\n{GREEN}{BOLD}┌─ OPTIMIZED LLVM IR ({opt_lines} lines) ─────────────────────┐{RESET}")
    print(f"{DIM}{optimized_ir}{RESET}")
    print(f"{GREEN}{BOLD}└───────────────────────────────────────────────────────┘{RESET}")

    # Native Assembly
    print(f"\n{MAGENTA}{BOLD}┌─ NATIVE ASSEMBLY ({asm_lines} lines) ──────────────────────┐{RESET}")
    print(f"{DIM}{asm_code}{RESET}")
    print(f"{MAGENTA}{BOLD}└───────────────────────────────────────────────────────┘{RESET}")

    # Metrics Summary
    print(f"\n{CYAN}{BOLD}┌─ OPTIMIZATION METRICS ─────────────────────────────────┐{RESET}")
    print(f"  {YELLOW}Instructions (before): {RESET}{before}")
    print(f"  {GREEN}Instructions (after):  {RESET}{after}")
    print(f"  {GREEN}Eliminated:            {RESET}{eliminated} instructions ({pct:.1f}% reduction)")
    print(f"  {CYAN}Raw IR lines:          {RESET}{raw_lines}")
    print(f"  {CYAN}Optimized IR lines:    {RESET}{opt_lines}")
    print(f"  {CYAN}Assembly lines:        {RESET}{asm_lines}")
    print(f"{CYAN}{BOLD}└───────────────────────────────────────────────────────┘{RESET}\n")


def main():
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print(f"{RED}Error: File '{filepath}' not found.{RESET}")
            sys.exit(1)
        with open(filepath, 'r') as f:
            source = f.read()
        title = os.path.basename(filepath)
    else:
        # Built-in demo
        source = """\
let volume = 100
let time = 0

while volume > 50 {
    volume = volume - 10
    time = time + 1
}

return time
"""
        title = "Built-in Demo (countdown loop)"

    explore_ir(source, title)


if __name__ == "__main__":
    main()

