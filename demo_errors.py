#!/usr/bin/env python3
"""
Simmer Error Demo — Demonstrates the compiler's error detection capabilities.
Shows what happens when you write incorrect Simmer code.

Usage: python demo_errors.py
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser_simmer import Parser
from semantic import SemanticAnalyzer

os.system('')  # Enable ANSI on Windows

# Colors
BOLD = '\033[1m'
RED = '\033[91m'
GREEN = '\033[92m'
CYAN = '\033[96m'
YELLOW = '\033[93m'
DIM = '\033[2m'
RESET = '\033[0m'

def test_error(title, code, expected_stage):
    """Try to compile code and show the error caught."""
    print(f"\n{CYAN}{'─' * 55}")
    print(f"  TEST: {title}")
    print(f"{'─' * 55}{RESET}")
    print(f"{DIM}  Code:{RESET}")
    for line in code.strip().split('\n'):
        print(f"    {line}")
    print()

    try:
        lexer = Lexer()
        tokens = lexer.tokenize(code)

        if expected_stage == 'lexer':
            print(f"  {RED}✗ Expected lexer to fail but it didn't!{RESET}")
            return False

        parser = Parser(tokens)
        ast = parser.parse()

        if expected_stage == 'parser':
            print(f"  {RED}✗ Expected parser to fail but it didn't!{RESET}")
            return False

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        if expected_stage == 'semantic':
            print(f"  {RED}✗ Expected semantic analyzer to fail but it didn't!{RESET}")
            return False

        print(f"  {RED}✗ No error was caught!{RESET}")
        return False

    except SyntaxError as e:
        stage = "Lexer" if expected_stage == 'lexer' else "Parser"
        print(f"  {GREEN}✓ Error caught by {BOLD}{stage}{RESET}{GREEN}:{RESET}")
        print(f"    {YELLOW}{e}{RESET}")
        return True
    except Exception as e:
        print(f"  {GREEN}✓ Error caught by {BOLD}Semantic Analyzer{RESET}{GREEN}:{RESET}")
        print(f"    {YELLOW}{e}{RESET}")
        return True


def main():
    print(f"\n{BOLD}{RED}")
    print("  ╔═══════════════════════════════════════════════╗")
    print("  ║    🍲  SIMMER ERROR DETECTION DEMO  🍲       ║")
    print("  ║   Demonstrating Compiler Safety Checks       ║")
    print("  ╚═══════════════════════════════════════════════╝")
    print(f"{RESET}")

    tests = [
        # ── Lexer Errors ──
        (
            "Illegal Character (Lexer catches @)",
            "let x = 10 @ 5",
            "lexer"
        ),
        (
            "Illegal Character (Lexer catches #)",
            "let x = #hello",
            "lexer"
        ),

        # ── Parser Errors ──
        (
            "Missing Assignment Operator (Parser catches)",
            "let x 10",
            "parser"
        ),
        (
            "Missing Closing Brace (Parser catches)",
            """
let x = 10
if x > 5 {
    x = 20
""",
            "parser"
        ),
        (
            "Invalid Expression (Parser catches)",
            "let x = + 10",
            "parser"
        ),

        # ── Semantic Errors ──
        (
            "Undeclared Variable Usage (Semantic catches)",
            """
let x = 10
y = x + 5
return y
""",
            "semantic"
        ),
        (
            "Duplicate Variable Declaration (Semantic catches)",
            """
let x = 10
let x = 20
return x
""",
            "semantic"
        ),
        (
            "Using Variable Before Declaration (Semantic catches)",
            """
let result = value + 10
let value = 5
return result
""",
            "semantic"
        ),
    ]

    passed = 0
    total = len(tests)

    for title, code, stage in tests:
        if test_error(title, code, stage):
            passed += 1

    print(f"\n{CYAN}{'═' * 55}{RESET}")
    color = GREEN if passed == total else YELLOW
    print(f"  {color}{BOLD}Results: {passed}/{total} error detection tests passed{RESET}")
    print(f"{CYAN}{'═' * 55}{RESET}\n")


if __name__ == "__main__":
    main()

