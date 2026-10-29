#!/usr/bin/env python3
"""
Simmer AST Visualizer — Pretty-prints the Abstract Syntax Tree.
Shows the hierarchical structure of parsed Simmer code.

Usage: python ast_visualizer.py <source_file.sim>
       python ast_visualizer.py              # Uses built-in demo
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser_simmer import *

os.system('')

# Colors
BOLD    = '\033[1m'
RED     = '\033[91m'
GREEN   = '\033[92m'
CYAN    = '\033[96m'
YELLOW  = '\033[93m'
MAGENTA = '\033[95m'
BLUE    = '\033[94m'
DIM     = '\033[2m'
RESET   = '\033[0m'


def pretty_print_ast(node, indent=0, prefix="", is_last=True):
    """Recursively pretty-print an AST node as a tree."""
    connector = "└── " if is_last else "├── "
    continuation = "    " if is_last else "│   "
    
    if indent == 0:
        line_prefix = ""
        child_prefix = ""
    else:
        line_prefix = prefix + connector
        child_prefix = prefix + continuation

    if isinstance(node, Program):
        print(f"{line_prefix}{MAGENTA}{BOLD}Program{RESET}")
        for i, stmt in enumerate(node.statements):
            pretty_print_ast(stmt, indent + 1, child_prefix, i == len(node.statements) - 1)

    elif isinstance(node, Declaration):
        print(f"{line_prefix}{CYAN}{BOLD}Declaration{RESET} {DIM}(let {node.name}){RESET}")
        print(f"{child_prefix}├── {YELLOW}name:{RESET} {node.name}")
        print(f"{child_prefix}└── {YELLOW}value:{RESET}")
        pretty_print_ast(node.value, indent + 2, child_prefix + "    ", True)

    elif isinstance(node, Assignment):
        print(f"{line_prefix}{BLUE}{BOLD}Assignment{RESET} {DIM}({node.name} = ...){RESET}")
        print(f"{child_prefix}├── {YELLOW}target:{RESET} {node.name}")
        print(f"{child_prefix}└── {YELLOW}value:{RESET}")
        pretty_print_ast(node.value, indent + 2, child_prefix + "    ", True)

    elif isinstance(node, Return):
        print(f"{line_prefix}{RED}{BOLD}Return{RESET}")
        print(f"{child_prefix}└── {YELLOW}value:{RESET}")
        pretty_print_ast(node.value, indent + 2, child_prefix + "    ", True)

    elif isinstance(node, BinOp):
        print(f"{line_prefix}{GREEN}{BOLD}BinOp{RESET} {DIM}[{node.op}]{RESET}")
        print(f"{child_prefix}├── {YELLOW}left:{RESET}")
        pretty_print_ast(node.left, indent + 2, child_prefix + "│   ", False)
        print(f"{child_prefix}└── {YELLOW}right:{RESET}")
        pretty_print_ast(node.right, indent + 2, child_prefix + "    ", True)

    elif isinstance(node, Number):
        print(f"{line_prefix}{GREEN}Number{RESET}({BOLD}{node.value}{RESET})")

    elif isinstance(node, Identifier):
        print(f"{line_prefix}{CYAN}Identifier{RESET}({BOLD}{node.name}{RESET})")

    elif isinstance(node, Condition):
        print(f"{line_prefix}{YELLOW}{BOLD}Condition{RESET} {DIM}[{node.op}]{RESET}")
        print(f"{child_prefix}├── {YELLOW}left:{RESET}")
        pretty_print_ast(node.left, indent + 2, child_prefix + "│   ", False)
        print(f"{child_prefix}└── {YELLOW}right:{RESET}")
        pretty_print_ast(node.right, indent + 2, child_prefix + "    ", True)

    elif isinstance(node, IfElse):
        print(f"{line_prefix}{MAGENTA}{BOLD}IfElse{RESET}")
        print(f"{child_prefix}├── {YELLOW}condition:{RESET}")
        pretty_print_ast(node.condition, indent + 2, child_prefix + "│   ", False)
        print(f"{child_prefix}├── {YELLOW}then ({len(node.then_body)} stmts):{RESET}")
        for i, stmt in enumerate(node.then_body):
            pretty_print_ast(stmt, indent + 2, child_prefix + "│   ", i == len(node.then_body) - 1)
        has_else = len(node.else_body) > 0
        if has_else:
            print(f"{child_prefix}└── {YELLOW}else ({len(node.else_body)} stmts):{RESET}")
            for i, stmt in enumerate(node.else_body):
                pretty_print_ast(stmt, indent + 2, child_prefix + "    ", i == len(node.else_body) - 1)
        else:
            print(f"{child_prefix}└── {DIM}(no else branch){RESET}")

    elif isinstance(node, WhileLoop):
        print(f"{line_prefix}{BLUE}{BOLD}WhileLoop{RESET}")
        print(f"{child_prefix}├── {YELLOW}condition:{RESET}")
        pretty_print_ast(node.condition, indent + 2, child_prefix + "│   ", False)
        print(f"{child_prefix}└── {YELLOW}body ({len(node.body)} stmts):{RESET}")
        for i, stmt in enumerate(node.body):
            pretty_print_ast(stmt, indent + 2, child_prefix + "    ", i == len(node.body) - 1)

    # Handle ForLoop if it exists (new feature)
    elif hasattr(node, '__class__') and node.__class__.__name__ == 'ForLoop':
        print(f"{line_prefix}{BLUE}{BOLD}ForLoop{RESET} {DIM}({node.var_name}){RESET}")
        print(f"{child_prefix}├── {YELLOW}start:{RESET}")
        pretty_print_ast(node.start, indent + 2, child_prefix + "│   ", False)
        print(f"{child_prefix}├── {YELLOW}end:{RESET}")
        pretty_print_ast(node.end, indent + 2, child_prefix + "│   ", False)
        print(f"{child_prefix}└── {YELLOW}body ({len(node.body)} stmts):{RESET}")
        for i, stmt in enumerate(node.body):
            pretty_print_ast(stmt, indent + 2, child_prefix + "    ", i == len(node.body) - 1)

    # Handle Print if it exists (new feature)
    elif hasattr(node, '__class__') and node.__class__.__name__ == 'Print':
        print(f"{line_prefix}{GREEN}{BOLD}Print{RESET}")
        print(f"{child_prefix}└── {YELLOW}value:{RESET}")
        pretty_print_ast(node.value, indent + 2, child_prefix + "    ", True)

    else:
        print(f"{line_prefix}{DIM}{node}{RESET}")


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
        source = """\
let volume = 100
let time = 0

while volume > 50 {
    volume = volume - 10
    time = time + 1
}

if time > 3 {
    time = time * 2
} else {
    time = 0
}

return time
"""
        title = "Built-in Demo"

    # Tokenize and parse
    lexer = Lexer()
    tokens = lexer.tokenize(source)
    parser = Parser(tokens)
    ast = parser.parse()

    print(f"\n{MAGENTA}{BOLD}{'═' * 55}")
    print(f"  SIMMER AST VISUALIZER — {title}")
    print(f"{'═' * 55}{RESET}")

    # Show source
    print(f"\n{CYAN}{BOLD}Source Code:{RESET}")
    for i, line in enumerate(source.strip().split('\n'), 1):
        print(f"  {DIM}{i:3d} │{RESET} {line}")

    # Show tokens
    print(f"\n{YELLOW}{BOLD}Tokens ({len(tokens)}):{RESET}")
    for tok in tokens:
        print(f"  {tok}")

    # Show AST tree
    print(f"\n{GREEN}{BOLD}Abstract Syntax Tree:{RESET}\n")
    pretty_print_ast(ast)
    print()


if __name__ == "__main__":
    main()

