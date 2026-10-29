#!/usr/bin/env python3
"""
Simmer Compiler — Automated Test Suite
========================================
Runs a battery of test programs through the full compiler pipeline
and validates the return values.

Usage: python test_suite.py
"""

import sys
import os
import ctypes
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

os.system('')  # Enable ANSI on Windows

# Colors
BOLD  = '\033[1m'
RED   = '\033[91m'
GREEN = '\033[92m'
CYAN  = '\033[96m'
YELLOW = '\033[93m'
DIM   = '\033[2m'
RESET = '\033[0m'

# Initialize LLVM once
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

def compile_and_run(source_code):
    """Compile source code and return the JIT execution result."""
    lexer = Lexer()
    tokens = lexer.tokenize(source_code)

    parser = Parser(tokens)
    ast = parser.parse()

    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)

    codegen = CodeGen()
    codegen.generate(ast)
    raw_ir = str(codegen.module)

    parsed_module = llvm.parse_assembly(raw_ir)
    parsed_module.verify()

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()

    # Optimize
    pto = llvm.create_pipeline_tuning_options(speed_level=3)
    pass_builder = llvm.create_pass_builder(target_machine, pto)
    pass_manager = pass_builder.getModulePassManager()
    pass_manager.run(parsed_module, pass_builder)

    # JIT Execute
    engine = llvm.create_mcjit_compiler(parsed_module, target_machine)
    engine.finalize_object()
    engine.run_static_constructors()

    func_ptr = engine.get_function_address("main")
    cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(func_ptr)
    return cfunc()

# ──────────────────────────────────────────────
#  Test Cases: (name, source_code, expected_result)
# ──────────────────────────────────────────────
TESTS = [
    # ── Basic Arithmetic ──
    (
        "Addition",
        "let a = 3\nlet b = 7\nreturn a + b",
        10
    ),
    (
        "Subtraction",
        "let a = 20\nlet b = 8\nreturn a - b",
        12
    ),
    (
        "Multiplication",
        "let a = 6\nlet b = 7\nreturn a * b",
        42
    ),
    (
        "Division",
        "let a = 100\nlet b = 4\nreturn a / b",
        25
    ),
    (
        "Complex Expression",
        "let a = 2\nlet b = 3\nlet c = a * b + a\nreturn c",
        8
    ),
    (
        "Chained Arithmetic",
        "let x = 10\nlet y = x + x + x\nreturn y",
        30
    ),

    # ── Variables & Assignment ──
    (
        "Variable Reassignment",
        "let x = 5\nx = x + 10\nreturn x",
        15
    ),
    (
        "Multiple Variables",
        "let a = 1\nlet b = 2\nlet c = 3\nlet d = a + b + c\nreturn d",
        6
    ),

    # ── If-Else ──
    (
        "If-True Branch",
        "let x = 10\nlet r = 0\nif x > 5 {\n  r = 1\n} else {\n  r = 0\n}\nreturn r",
        1
    ),
    (
        "If-False Branch",
        "let x = 3\nlet r = 0\nif x > 5 {\n  r = 1\n} else {\n  r = 0\n}\nreturn r",
        0
    ),
    (
        "If Without Else",
        "let x = 10\nlet r = 0\nif x > 5 {\n  r = 42\n}\nreturn r",
        42
    ),
    (
        "Nested If-Else",
        "let x = 50\nlet r = 0\nif x > 80 {\n  r = 3\n} else {\n  if x > 40 {\n    r = 2\n  } else {\n    r = 1\n  }\n}\nreturn r",
        2
    ),

    # ── While Loops ──
    (
        "Simple While Loop",
        "let i = 0\nwhile i < 5 {\n  i = i + 1\n}\nreturn i",
        5
    ),
    (
        "Countdown Loop",
        "let volume = 100\nlet time = 0\nwhile volume > 50 {\n  volume = volume - 10\n  time = time + 1\n}\nreturn time",
        5
    ),
    (
        "Factorial (6! = 720)",
        "let n = 6\nlet fact = 1\nwhile n > 1 {\n  fact = fact * n\n  n = n - 1\n}\nreturn fact",
        720
    ),
    (
        "Fibonacci (10th)",
        "let n = 10\nlet a = 0\nlet b = 1\nlet i = 2\nlet temp = 0\nwhile i <= n {\n  temp = a + b\n  a = b\n  b = temp\n  i = i + 1\n}\nreturn b",
        55
    ),

    # ── Power Computation ──
    (
        "Power (2^10 = 1024)",
        "let base = 2\nlet exp = 10\nlet result = 1\nwhile exp > 0 {\n  result = result * base\n  exp = exp - 1\n}\nreturn result",
        1024
    ),

    # ── Comparison Operators ──
    (
        "Less-Than-Equal",
        "let x = 5\nlet r = 0\nif x <= 5 {\n  r = 1\n}\nreturn r",
        1
    ),
    (
        "Greater-Than-Equal",
        "let x = 10\nlet r = 0\nif x >= 10 {\n  r = 1\n}\nreturn r",
        1
    ),
    (
        "Equality Check",
        "let x = 42\nlet r = 0\nif x == 42 {\n  r = 1\n}\nreturn r",
        1
    ),

    # ── GCD (Euclidean Algorithm) ──
    (
        "GCD(48, 18) = 6",
        "let a = 48\nlet b = 18\nlet temp = 0\nwhile b > 0 {\n  temp = b\n  b = a - (a / b) * b\n  a = temp\n}\nreturn a",
        6
    ),

    # ── New Language Features ──
    (
        "Modulo Operator (%)",
        "let a = 17\nlet b = 5\nreturn a % b",
        2
    ),
    (
        "Parenthesized Expression",
        "let a = 2\nlet b = 3\nlet c = 4\nreturn (a + b) * c",
        20
    ),
    (
        "Not-Equal Comparison (!=)",
        "let x = 10\nlet r = 0\nif x != 5 {\n  r = 1\n}\nreturn r",
        1
    ),
    (
        "For Loop (Sum 1 to 10)",
        "let sum = 0\nlet i = 0\nfor i = 1 to 11 {\n  sum = sum + i\n}\nreturn sum",
        55
    ),
    (
        "Single-line Comments (//)",
        "// Initialize variables\nlet x = 100 // initial value\nlet y = 50\n// Compute difference\nreturn x - y",
        50
    ),
    (
        "Print Statement Support",
        "let x = 42\nprint x\nreturn x",
        42
    ),

    # ── Edge Cases ──
    (
        "Return Constant Zero",
        "return 0",
        0
    ),
    (
        "Return Constant",
        "return 42",
        42
    ),
    (
        "Single Variable Return",
        "let x = 99\nreturn x",
        99
    ),
]

def main():
    print(f"\n{BOLD}{CYAN}")
    print("  ╔═══════════════════════════════════════════════╗")
    print("  ║      🍲  SIMMER COMPILER TEST SUITE  🍲     ║")
    print("  ║     Automated Correctness Verification       ║")
    print("  ╚═══════════════════════════════════════════════╝")
    print(f"{RESET}")

    passed = 0
    failed = 0
    errors = []

    for name, code, expected in TESTS:
        try:
            # Suppress any stdout from the compiled program (e.g., print statements)
            with contextlib.redirect_stdout(io.StringIO()):
                result = compile_and_run(code)

            if result == expected:
                print(f"  {GREEN}✓ PASS{RESET}  {name} {DIM}(got {result}){RESET}")
                passed += 1
            else:
                print(f"  {RED}✗ FAIL{RESET}  {name} {DIM}(expected {expected}, got {result}){RESET}")
                failed += 1
                errors.append((name, expected, result))
        except Exception as e:
            print(f"  {RED}✗ ERROR{RESET} {name} {DIM}({e}){RESET}")
            failed += 1
            errors.append((name, expected, str(e)))

    # Summary
    print(f"\n{CYAN}{'═' * 55}{RESET}")
    total = passed + failed
    if failed == 0:
        print(f"  {GREEN}{BOLD}ALL {total} TESTS PASSED ✓{RESET}")
    else:
        print(f"  {YELLOW}{BOLD}{passed}/{total} passed, {RED}{failed} failed{RESET}")
        print(f"\n  {RED}Failed tests:{RESET}")
        for name, expected, actual in errors:
            print(f"    • {name}: expected {expected}, got {actual}")
    print(f"{CYAN}{'═' * 55}{RESET}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

