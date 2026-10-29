#!/usr/bin/env python3
"""
Simmer Compiler — Full Demo Runner
===================================
Runs every .sim example through the complete compilation pipeline:
  Lex → Parse → Semantic Analysis → Code Generation → Optimization → JIT
Displays detailed output for each stage and a summary table at the end.

Usage:
    python demo.py              # Run all examples
    python demo.py 05_fibonacci # Run a single example by name fragment
"""

import os
import sys
import glob
import ctypes
import traceback

# ---------------------------------------------------------------------------
# ANSI colour helpers (safe on modern Windows 10+ terminals)
# ---------------------------------------------------------------------------
# Enable ANSI escape sequences on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.system("color")  # quick trick to enable VT100 on older Windows builds
    try:
        import ctypes as _ct
        _kernel32 = _ct.windll.kernel32
        _kernel32.SetConsoleMode(_kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# Colour codes
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"
BG_BLUE = "\033[44m"
BG_MAG  = "\033[45m"


def colour(text, *codes):
    """Wrap *text* in the given ANSI codes."""
    return "".join(codes) + str(text) + RESET


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
BANNER = rf"""
{CYAN}{BOLD}
  ███████╗██╗███╗   ███╗███╗   ███╗███████╗██████╗
  ██╔════╝██║████╗ ████║████╗ ████║██╔════╝██╔══██╗
  ███████╗██║██╔████╔██║██╔████╔██║█████╗  ██████╔╝
  ╚════██║██║██║╚██╔╝██║██║╚██╔╝██║██╔══╝  ██╔══██╗
  ███████║██║██║ ╚═╝ ██║██║ ╚═╝ ██║███████╗██║  ██║
  ╚══════╝╚═╝╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝
{RESET}
{BOLD}{MAGENTA}  ╔══════════════════════════════════════════════════╗
  ║     SIMMER COMPILER — Full Demo Runner           ║
  ║     LLVM-backed · Optimising · JIT-compiled      ║
  ╚══════════════════════════════════════════════════╝{RESET}
"""


# ---------------------------------------------------------------------------
# Locate compiler modules — they live in the same directory as this script
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from lexer import Lexer
from parser_simmer import Parser
from semantic import SemanticAnalyzer
from codegen import CodeGen

# llvmlite binding — initialise once
from llvmlite import binding as llvm

_llvm_initialised = False

def ensure_llvm():
    """Initialise the LLVM back-end exactly once."""
    global _llvm_initialised
    if not _llvm_initialised:
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        _llvm_initialised = True


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------
def count_instructions(ir_text: str) -> int:
    """Count 'active' IR instructions (lines containing '=' or 'ret')."""
    return len([l for l in ir_text.split("\n") if "=" in l or "ret" in l])


def section(title: str):
    """Print a section header."""
    width = 60
    print(f"\n{BOLD}{CYAN}{'─' * width}{RESET}")
    print(f"{BOLD}{CYAN}  ▸ {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")


def subsection(title: str):
    """Print a subsection header."""
    print(f"\n  {BOLD}{YELLOW}┌─ {title}{RESET}")


# ---------------------------------------------------------------------------
# Core compilation pipeline (returns dict with results or raises)
# ---------------------------------------------------------------------------
def compile_example(source_code: str, name: str, output_dir: str):
    """Run the full Simmer pipeline on *source_code*.

    Returns a dict with keys:
        tokens, ast, raw_ir, optimized_ir, result,
        instr_before, instr_after, asm_file, obj_file
    """
    ensure_llvm()
    info = {}

    # 1. Lex ----------------------------------------------------------------
    lexer = Lexer()
    tokens = lexer.tokenize(source_code)
    info["tokens"] = tokens

    # 2. Parse --------------------------------------------------------------
    parser = Parser(tokens)
    ast = parser.parse()
    info["ast"] = ast

    # 3. Semantic Analysis --------------------------------------------------
    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)

    # 4. Code Generation ----------------------------------------------------
    cg = CodeGen()
    cg.generate(ast)
    raw_ir = str(cg.module)
    info["raw_ir"] = raw_ir

    # 5. Optimisation -------------------------------------------------------
    parsed_module = llvm.parse_assembly(raw_ir)
    parsed_module.verify()

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()

    pto = llvm.create_pipeline_tuning_options(speed_level=3)
    pb  = llvm.create_pass_builder(target_machine, pto)
    pm  = pb.getModulePassManager()
    pm.run(parsed_module, pb)

    optimized_ir = str(parsed_module)
    info["optimized_ir"] = optimized_ir
    info["instr_before"] = count_instructions(raw_ir)
    info["instr_after"]  = count_instructions(optimized_ir)

    # 6. JIT Execution ------------------------------------------------------
    engine = llvm.create_mcjit_compiler(parsed_module, target_machine)
    engine.finalize_object()
    engine.run_static_constructors()

    func_ptr = engine.get_function_address("main")
    cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(func_ptr)
    result = cfunc()
    info["result"] = result

    # 7. Disk Emission (assembly + object) ----------------------------------
    # We need a fresh parsed module for emission since the JIT consumed the
    # previous one — re-parse the optimized IR.
    emit_mod = llvm.parse_assembly(optimized_ir)
    emit_mod.verify()
    emit_target = llvm.Target.from_default_triple()
    emit_tm = emit_target.create_target_machine()

    os.makedirs(output_dir, exist_ok=True)
    asm_path = os.path.join(output_dir, f"{name}.s")
    obj_path = os.path.join(output_dir, f"{name}.o")

    asm_code = emit_tm.emit_assembly(emit_mod)
    with open(asm_path, "w") as f:
        f.write(asm_code)
    info["asm_file"] = asm_path

    obj_code = emit_tm.emit_object(emit_mod)
    with open(obj_path, "wb") as f:
        f.write(obj_code)
    info["obj_file"] = obj_path

    return info


# ---------------------------------------------------------------------------
# Pretty-print a single example run
# ---------------------------------------------------------------------------
def display_example(filepath: str, info: dict):
    """Print detailed compilation output for one example."""
    with open(filepath, "r") as f:
        source = f.read()

    # ── Source code ────────────────────────────────────────────────────────
    subsection("Source Code")
    for i, line in enumerate(source.strip().splitlines(), 1):
        print(f"  {DIM}│{RESET}  {DIM}{i:3d}{RESET}  {line}")

    # ── Tokens ────────────────────────────────────────────────────────────
    subsection(f"Lexer Tokens  ({len(info['tokens'])} tokens)")
    # Show tokens in a compact grid
    per_row = 4
    toks = info["tokens"]
    for i in range(0, len(toks), per_row):
        row = "  │  ".join(f"{colour(t.type, DIM):>26s} {colour(t.value, GREEN)}"
                           for t in toks[i:i + per_row])
        print(f"  {DIM}│{RESET}  {row}")

    # ── AST ───────────────────────────────────────────────────────────────
    subsection("Abstract Syntax Tree")
    for stmt in info["ast"].statements:
        print(f"  {DIM}│{RESET}  {YELLOW}{stmt}{RESET}")

    # ── Raw LLVM IR ───────────────────────────────────────────────────────
    subsection("LLVM IR  (before optimisation)")
    for line in info["raw_ir"].strip().splitlines():
        print(f"  {DIM}│{RESET}  {DIM}{line}{RESET}")

    # ── Optimised LLVM IR ─────────────────────────────────────────────────
    subsection("LLVM IR  (after optimisation)")
    for line in info["optimized_ir"].strip().splitlines():
        print(f"  {DIM}│{RESET}  {GREEN}{line}{RESET}")

    # ── Metrics ───────────────────────────────────────────────────────────
    before = info["instr_before"]
    after  = info["instr_after"]
    reduction = ((before - after) / before * 100) if before else 0.0
    subsection("Optimisation Metrics")
    print(f"  {DIM}│{RESET}  Instructions before : {BOLD}{before}{RESET}")
    print(f"  {DIM}│{RESET}  Instructions after  : {BOLD}{after}{RESET}")
    print(f"  {DIM}│{RESET}  Reduction           : {BOLD}{MAGENTA}{reduction:.1f}%{RESET}")

    # ── JIT result ────────────────────────────────────────────────────────
    subsection("JIT Execution Result")
    print(f"  {DIM}│{RESET}  Return value: {BOLD}{GREEN}{info['result']}{RESET}")

    # ── Disk emission ─────────────────────────────────────────────────────
    subsection("Disk Emission")
    print(f"  {DIM}│{RESET}  Assembly → {CYAN}{info['asm_file']}{RESET}")
    print(f"  {DIM}│{RESET}  Object   → {CYAN}{info['obj_file']}{RESET}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(BANNER)

    examples_dir = os.path.join(SCRIPT_DIR, "examples")
    output_dir   = os.path.join(SCRIPT_DIR, "output")

    # Discover .sim files sorted by name
    sim_files = sorted(glob.glob(os.path.join(examples_dir, "*.sim")))
    if not sim_files:
        print(colour("  No .sim files found in examples/", RED, BOLD))
        sys.exit(1)

    # Optional filter: pass a substring to run only matching examples
    filter_text = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
    if filter_text:
        sim_files = [f for f in sim_files
                     if filter_text.lower() in os.path.basename(f).lower()]
        if not sim_files:
            print(colour(f"  No examples matched '{filter_text}'", RED, BOLD))
            sys.exit(1)

    print(f"  {BOLD}Found {len(sim_files)} example(s) in {examples_dir}{RESET}\n")

    # ── Results accumulator for the summary table ─────────────────────────
    results = []  # list of dicts or error entries

    for idx, filepath in enumerate(sim_files, 1):
        filename = os.path.basename(filepath)
        name     = os.path.splitext(filename)[0]

        # Read the first comment line as the description
        with open(filepath, "r") as f:
            first_line = f.readline().strip()
        description = first_line.lstrip("/").strip() if first_line.startswith("//") else filename

        section(f"[{idx}/{len(sim_files)}]  {filename}  —  {description}")

        try:
            with open(filepath, "r") as f:
                source = f.read()

            info = compile_example(source, name, output_dir)
            display_example(filepath, info)
            results.append({
                "name": filename,
                "result": info["result"],
                "before": info["instr_before"],
                "after":  info["instr_after"],
                "status": "OK",
            })

        except Exception as exc:
            print(f"\n  {RED}{BOLD}✗ FAILED:{RESET} {RED}{exc}{RESET}")
            print(f"  {DIM}{traceback.format_exc()}{RESET}")
            results.append({
                "name": filename,
                "result": "ERR",
                "before": "-",
                "after":  "-",
                "status": str(exc)[:60],
            })

    # ── Summary table ─────────────────────────────────────────────────────
    print(f"\n\n{BOLD}{MAGENTA}{'═' * 90}{RESET}")
    print(f"{BOLD}{MAGENTA}  SUMMARY{RESET}")
    print(f"{BOLD}{MAGENTA}{'═' * 90}{RESET}")

    hdr = (f"  {'Example':<26s} {'Return':>8s} {'Instr Before':>14s} "
           f"{'Instr After':>13s} {'Reduction':>11s}  {'Status'}")
    print(f"\n{BOLD}{WHITE}{hdr}{RESET}")
    print(f"  {'─' * 86}")

    for r in results:
        if r["result"] == "ERR":
            print(f"  {r['name']:<26s} {RED}{'ERR':>8s}{RESET}"
                  f" {'─':>14s} {'─':>13s} {'─':>11s}  {RED}{r['status']}{RESET}")
        else:
            before = r["before"]
            after  = r["after"]
            reduction = ((before - after) / before * 100) if before else 0.0
            status_colour = GREEN if reduction > 0 else YELLOW
            print(f"  {r['name']:<26s} {GREEN}{r['result']:>8}{RESET}"
                  f" {before:>14} {after:>13}"
                  f" {status_colour}{reduction:>10.1f}%{RESET}"
                  f"  {GREEN}OK{RESET}")

    print(f"  {'─' * 86}")

    passed = sum(1 for r in results if r["result"] != "ERR")
    failed = len(results) - passed
    print(f"\n  {BOLD}{GREEN}✓ {passed} passed{RESET}", end="")
    if failed:
        print(f"  {BOLD}{RED}✗ {failed} failed{RESET}", end="")
    print(f"  {DIM}(output saved to {output_dir}){RESET}\n")


if __name__ == "__main__":
    main()
