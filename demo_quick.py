#!/usr/bin/env python3
"""
Simmer Compiler — Quick Demo Runner
====================================
Compiles every .sim example and prints a compact one-line summary per file.
Ideal for live presentations — fast and focused.

Usage:
    python demo_quick.py
"""

import os
import sys
import glob
import ctypes
import traceback

# ---------------------------------------------------------------------------
# ANSI colour setup (Windows-safe)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.system("color")
    try:
        import ctypes as _ct
        _kernel32 = _ct.windll.kernel32
        _kernel32.SetConsoleMode(_kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"


# ---------------------------------------------------------------------------
# Locate compiler modules
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from lexer import Lexer
from parser_simmer import Parser
from semantic import SemanticAnalyzer
from codegen import CodeGen
from llvmlite import binding as llvm

_llvm_initialised = False

def ensure_llvm():
    global _llvm_initialised
    if not _llvm_initialised:
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        _llvm_initialised = True


def count_instructions(ir_text: str) -> int:
    return len([l for l in ir_text.split("\n") if "=" in l or "ret" in l])


# ---------------------------------------------------------------------------
# Quick compile — returns (result, instr_before, instr_after)
# ---------------------------------------------------------------------------
def quick_compile(source_code: str):
    """Run the pipeline and return (return_value, before, after)."""
    ensure_llvm()

    tokens = Lexer().tokenize(source_code)
    ast = Parser(tokens).parse()
    SemanticAnalyzer().analyze(ast)

    cg = CodeGen()
    cg.generate(ast)
    raw_ir = str(cg.module)

    parsed = llvm.parse_assembly(raw_ir)
    parsed.verify()

    target = llvm.Target.from_default_triple()
    tm = target.create_target_machine()

    pto = llvm.create_pipeline_tuning_options(speed_level=3)
    pb  = llvm.create_pass_builder(tm, pto)
    pm  = pb.getModulePassManager()
    pm.run(parsed, pb)

    optimized_ir = str(parsed)

    before = count_instructions(raw_ir)
    after  = count_instructions(optimized_ir)

    engine = llvm.create_mcjit_compiler(parsed, tm)
    engine.finalize_object()
    engine.run_static_constructors()

    func_ptr = engine.get_function_address("main")
    cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(func_ptr)
    result = cfunc()

    return result, before, after


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # Mini banner
    print(f"""
{CYAN}{BOLD}  ┌──────────────────────────────────────────────┐
  │   🔥  SIMMER COMPILER — Quick Demo            │
  │       Compile · Optimise · Execute             │
  └──────────────────────────────────────────────┘{RESET}
""")

    examples_dir = os.path.join(SCRIPT_DIR, "examples")
    sim_files = sorted(glob.glob(os.path.join(examples_dir, "*.sim")))

    if not sim_files:
        print(f"  {RED}No .sim files found in examples/{RESET}")
        sys.exit(1)

    # Header
    hdr = (f"  {'#':<4s} {'Example':<26s} {'Description':<42s} "
           f"{'Result':>8s} {'Opt %':>7s}  {'Status'}")
    print(f"{BOLD}{WHITE}{hdr}{RESET}")
    print(f"  {'─' * 100}")

    results = []

    for idx, filepath in enumerate(sim_files, 1):
        filename = os.path.basename(filepath)

        # Extract description from first comment
        with open(filepath, "r") as f:
            first_line = f.readline().strip()
        desc = first_line.lstrip("/").strip() if first_line.startswith("//") else ""
        desc = desc[:40]  # truncate for table

        try:
            with open(filepath, "r") as f:
                source = f.read()
            result, before, after = quick_compile(source)
            reduction = ((before - after) / before * 100) if before else 0.0

            colour = GREEN if reduction > 0 else YELLOW
            print(f"  {idx:<4d} {filename:<26s} {DIM}{desc:<42s}{RESET} "
                  f"{GREEN}{result:>8d}{RESET} "
                  f"{colour}{reduction:>6.1f}%{RESET}  {GREEN}✓{RESET}")
            results.append(("OK", result, reduction))

        except Exception as exc:
            err_msg = str(exc)[:50]
            print(f"  {idx:<4d} {filename:<26s} {DIM}{desc:<42s}{RESET} "
                  f"{RED}{'ERR':>8s}{RESET} "
                  f"{'─':>7s}  {RED}✗ {err_msg}{RESET}")
            results.append(("ERR", None, None))

    print(f"  {'─' * 100}")

    passed = sum(1 for s, _, _ in results if s == "OK")
    failed = len(results) - passed

    print(f"\n  {BOLD}{GREEN}✓ {passed} passed{RESET}", end="")
    if failed:
        print(f"  {BOLD}{RED}✗ {failed} failed{RESET}", end="")
    print(f"  {DIM}out of {len(results)} total{RESET}\n")


if __name__ == "__main__":
    main()
