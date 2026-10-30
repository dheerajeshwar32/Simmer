# 🍲 Simmer Compiler
> **A high-performance Domain-Specific Language (DSL) and compiler translating high-level scripts into optimized native machine code.**  
> Hand-rolled recursive-descent frontend · Industrial-grade LLVM backend · JIT & AOT execution.

[![Live Web Playground](https://img.shields.io/badge/Live%20Playground-Render-46E3B7.svg?style=for-the-badge&logo=render)](https://simmer-6v9k.onrender.com/)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-181717.svg?style=for-the-badge&logo=github)](https://github.com/dheerajeshwar32/Simmer)

[![Language](https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg)](https://python.org)
[![Backend](https://img.shields.io/badge/Backend-LLVM%20via%20llvmlite-green.svg)](https://llvmlite.readthedocs.io/)
[![Architecture](https://img.shields.io/badge/Architecture-x86__64%20%2F%20ARM64-orange.svg)]()
[![Tests](https://img.shields.io/badge/Tests-30%2F30%20Passing-brightgreen.svg)]()
[![Course](https://img.shields.io/badge/Course-BCSE307P%20Compiler%20Design-purple.svg)]()

> 🌐 **Live Web Playground**: [https://simmer-6v9k.onrender.com/](https://simmer-6v9k.onrender.com/)

---

## 👥 Authors
* **N. Dheeraj Eshwar** (24BCE2144)
* **G. Surya Prakash** (24BCE0744)

*School of Computer Science and Engineering — Compiler Design Lab (BCSE307P)*

---

## 📑 Table of Contents
1. [Project Overview](#-project-overview)
2. [Language Specification](#-language-specification)
3. [Compiler Architecture](#-compiler-architecture)
4. [Project Structure](#-project-structure)
5. [Installation & Setup](#-installation--setup)
6. [Interactive CLI Tools](#-interactive-cli-tools)
7. [Example Gallery (13 Programs)](#-example-gallery-13-programs)
8. [Optimization Deep-Dive](#-optimization-deep-dive)
9. [Error Detection & Safety](#-error-detection--safety)
10. [Presentation & Demo Playbook](#-presentation--demo-playbook)

---

## 🎯 Project Overview

Most academic compiler lab projects stop short in two critical ways:
1. **The Abstraction Gap:** Relying on automated parser generators (`Flex`/`Bison`, `Lex`/`Yacc`) which hide the inner mechanics of tokenization, recursive parsing, and AST construction.
2. **The Backend Disconnect:** Stopping at an Abstract Syntax Tree (AST) or writing a basic tree-walk interpreter, never producing real machine code for physical hardware.

**Simmer** bridges both gaps:
* **100% Hand-Rolled Frontend:** Lexer, recursive-descent parser, AST node definitions, and symbol-table semantic analyzer built from scratch without external parser libraries.
* **Production LLVM Backend:** Generates strongly-typed LLVM Intermediate Representation (IR), executes the modern LLVM `PassBuilder` (`-O3` optimization level), compiles to native machine code in-memory via Just-In-Time (JIT) execution, and emits physical assembly (`.s`) and machine object (`.o`) files to disk.

---

## 📜 Language Specification

### Keywords
`let` · `return` · `if` · `else` · `while` · `for` · `to` · `print`

### Operators
* **Arithmetic:** `+`, `-`, `*`, `/`, `%` (modulo)
* **Comparison:** `==`, `!=`, `<`, `>`, `<=`, `>=`
* **Assignment:** `=`

### Syntax & Grammar (EBNF)
```ebnf
Program        ::= Statement*
Statement      ::= VarDecl | Assignment | ReturnStmt | IfElseStmt | WhileStmt | ForStmt | PrintStmt

VarDecl        ::= "let" IDENTIFIER "=" Expression
Assignment     ::= IDENTIFIER "=" Expression
ReturnStmt     ::= "return" Expression
IfElseStmt     ::= "if" Condition "{" Statement* "}" [ "else" "{" Statement* "}" ]
WhileStmt      ::= "while" Condition "{" Statement* "}"
ForStmt        ::= "for" IDENTIFIER "=" Expression "to" Expression "{" Statement* "}"
PrintStmt      ::= "print" Expression

Condition      ::= Expression ("==" | "!=" | "<" | ">" | "<=" | ">=") Expression
Expression     ::= Term (("+" | "-") Term)*
Term           ::= Primary (("*" | "/" | "%") Primary)*
Primary        ::= NUMBER | IDENTIFIER | "(" Expression ")"
Comment        ::= "//" AnyCharacters*
```

---

## 🏗️ Compiler Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SIMMER COMPILER PIPELINE                        │
└────────────────────────────────────────────────────────────────────────┘

    Source Code (.sim)
           │
           ▼
    ┌───────────────┐
    │  1. Lexer     │  Regex tokenization; ignores whitespace & comments (//)
    │  (lexer.py)   │  Produces stream of typed Token objects
    └──────┬────────┘
           │
           ▼
    ┌───────────────┐
    │  2. Parser    │  Recursive-descent parsing with operator precedence
    │(parser_simmer)│  Constructs hierarchical Abstract Syntax Tree (AST)
    └──────┬────────┘
           │
           ▼
    ┌───────────────┐
    │ 3. Semantic   │  Symbol table validation; detects undeclared variables,
    │  (semantic.py)│  duplicate declarations, and scope violations
    └──────┬────────┘
           │
           ▼
    ┌───────────────┐
    │  4. Codegen   │  Transforms AST into strongly-typed LLVM IR (i32 types,
    │ (codegen.py)  │  alloca/load/store, basic blocks, phi/branch, printf)
    └──────┬────────┘
           │
           ▼
    ┌───────────────┐
    │ 5. Optimizer  │  LLVM PassBuilder at speed_level=3 (-O3): constant folding,
    │(optimizer.py) │  dead code elimination, instruction reduction
    └──────┬────────┘
           │
      ┌────┴──────────────────────────┐
      ▼                               ▼
┌──────────────┐              ┌──────────────┐
│ 6. JIT Exec  │              │ 7. AOT Emit  │
│ (MCJIT engine│              │ Saves .s asm │
│  via ctypes) │              │ & .o object  │
└──────────────┘              └──────────────┘
```

---

## 📁 Project Structure

```
simmer-compiler/
├── run_dashboard.py     # 🚀 ONE-CLICK LAUNCHER for Simmer Studio Web Dashboard
├── web/                 # Interactive Web UI & API Backend (Flask + Tailwind)
│   ├── app.py           # REST API endpoints for compilation & diagnostics
│   └── templates/       # Glassmorphism dark-mode UI with live AST visualizer
├── lexer.py             # Lexical analyzer (token definition & regex matcher)
├── parser_simmer.py     # Recursive-descent parser & AST node definitions
├── semantic.py          # Symbol-table semantic analyzer (visitor pattern)
├── codegen.py           # LLVM IR code generator (using llvmlite)
├── optimizer.py         # Standalone optimizer demonstration
├── simmer.py            # Primary CLI compiler driver with rich flags
├── demo.py              # Full visual demo runner with side-by-side IR
├── demo_quick.py        # Compact presentation runner with results table
├── demo_errors.py       # Error detection & safety check demonstrator
├── test_suite.py        # Automated test suite (30 comprehensive tests)
├── ast_visualizer.py    # ASCII tree visualization tool for AST
├── ir_explorer.py       # Side-by-side LLVM IR & assembly explorer
├── simmer_example.sim   # Introductory example script
├── examples/            # 13 verified benchmark scripts:
│   ├── 01_basics.sim
│   ├── 02_if_else.sim
│   ├── 03_while_loop.sim
│   ├── 04_nested_if.sim
│   ├── 05_fibonacci.sim
│   ├── 06_factorial.sim
│   ├── 07_prime_check.sim
│   ├── 08_gcd.sim
│   ├── 09_for_loop.sim
│   ├── 10_print_demo.sim
│   ├── 11_modulo.sim
│   ├── 12_power.sim
│   └── 13_collatz.sim
└── output/              # Emitted native assembly (.s) and object (.o) files
```

---

## 🚀 Installation & Setup

### Prerequisites
* Python 3.10 or higher
* Windows, macOS, or Linux

### Setup Virtual Environment
```bash
# Clone or navigate to the project directory
cd simmer-compiler

# Create and activate virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate

# Install LLVM Python bindings and Flask dashboard
pip install llvmlite flask
```

---

## 🖥️ Simmer Studio — Visual Web Dashboard (Recommended)

Launch the interactive compiler studio with a single command:
```bash
python run_dashboard.py
```
* **Auto-opens in your browser** at `http://127.0.0.1:5000`
* **Interactive Code Editor:** Write or modify Simmer scripts with line numbers and hotkey `Ctrl+Enter` to compile.
* **13 Built-in Benchmark Presets:** One-click loading of Fibonacci, Prime Check, Collatz, Factorial, GCD, etc.
* **Live Pipeline Inspector:**
  * 🔤 **Token Stream:** Filterable colored badges for KEYWORD, IDENTIFIER, NUMBER, OPERATOR.
  * 🌳 **Interactive AST:** Collapsible visual syntax tree showing nodes and precedence hierarchy.
  * 🛡️ **Symbol Table:** Real-time scope inspection verifying identifier declarations.
  * ⚡ **LLVM IR Diff:** Side-by-side comparison of unoptimized vs. `-O3` PassBuilder optimized IR.
  * ⚙️ **Native Assembly Viewer:** Real x86_64 assembly with one-click `.s` and `.o` binary downloads.
  * 🧪 **In-Browser Test Runner:** Live execution of all 30 automated correctness tests.

---

## 💻 Interactive CLI Tools

### 1. Main Compiler (`simmer.py`)
Compile and run any `.sim` file with detailed phase-by-phase reporting:
```bash
# Default compilation & JIT execution
python simmer.py simmer_example.sim

# Show lexer tokens
python simmer.py simmer_example.sim --tokens

# Show parsed AST
python simmer.py simmer_example.sim --ast

# Show raw and optimized LLVM IR
python simmer.py simmer_example.sim --ir

# Verbose mode: inspect EVERY stage of compilation
python simmer.py simmer_example.sim --verbose
```

### 2. Fast Presentation Demo (`demo_quick.py`)
Runs all 13 example programs and produces a clean live summary table:
```bash
python demo_quick.py
```

### 3. Detailed Visual Demo (`demo.py`)
Inspects tokens, AST, IR diff, JIT results, and emissions for any or all programs:
```bash
# Run all examples
python demo.py

# Run a specific benchmark (e.g. Fibonacci)
python demo.py 05_fibonacci
```

### 4. AST Tree Visualizer (`ast_visualizer.py`)
Prints a syntax tree showing node hierarchy, expressions, and branches:
```bash
python ast_visualizer.py examples/03_while_loop.sim
```

### 5. IR Explorer (`ir_explorer.py`)
Inspects how LLVM `-O3` PassBuilder transforms raw IR into optimized assembly:
```bash
python ir_explorer.py examples/05_fibonacci.sim
```

### 6. Error Detection Demo (`demo_errors.py`)
Proves the compiler catches syntax mistakes, illegal tokens, and semantic violations:
```bash
python demo_errors.py
```

### 7. Automated Test Suite (`test_suite.py`)
Runs 30 unit and integration tests across all language constructs:
```bash
python test_suite.py
```

---

## 📚 Example Gallery (13 Programs)

| # | Program | Description | Algorithmic Concept | Result | Optimization Gain |
|---|---|---|---|:---:|:---:|
| 01 | `01_basics.sim` | Arithmetic operations (`+`, `-`, `*`, `/`) | Constant propagation | `30` | **73.9%** |
| 02 | `02_if_else.sim` | Conditional branch execution | Branch pruning | `0` | **33.3%** |
| 03 | `03_while_loop.sim` | Countdown timer loop | Loop invariant reduction | `5` | **53.8%** |
| 04 | `04_nested_if.sim` | Multi-tier grading system | Nested branch merging | `3` | **53.8%** |
| 05 | `05_fibonacci.sim` | 10th Fibonacci number computation | Loop unrolling & constant evaluation | `55` | **70.0%** |
| 06 | `06_factorial.sim` | Factorial calculation (6! = 720) | Multiplicative accumulation | `720` | **57.1%** |
| 07 | `07_prime_check.sim` | Primality test for n=17 | Trial division algorithm | `1` | **73.9%** |
| 08 | `08_gcd.sim` | Greatest Common Divisor (48, 18) | Euclidean algorithm | `6` | **42.1%** |
| 09 | `09_for_loop.sim` | Sum of integers from 1 to 10 | Bounded iteration loop | `55` | **57.1%** |
| 10 | `10_print_demo.sim` | Runtime printing via external `printf` | Standard I/O interop | `126` | **60.9%** |
| 11 | `11_modulo.sim` | Remainder calculation (`17 % 5`) | Integer remainder instruction | `2` | **45.5%** |
| 12 | `12_power.sim` | Exponentiation (2^10 = 1024) | Repeated multiplication | `1024` | **60.0%** |
| 13 | `13_collatz.sim` | Collatz hailstone steps for n=27 | Dynamic arithmetic state loop | `111` | **22.7%** |

---

## ⚡ Optimization Deep-Dive

Simmer connects directly to LLVM's modern `PassBuilder` configured at `speed_level=3` (equivalent to `-O3`).

### Before vs. After Optimization Example (`05_fibonacci.sim`)

#### Raw LLVM IR (Unoptimized — 20 instructions):
```llvm
define i32 @"main"() {
entry:
  %"n" = alloca i32
  store i32 10, i32* %"n"
  %"a" = alloca i32
  store i32 0, i32* %"a"
  ...
loopcond:
  %"i_val" = load i32, i32* %"i"
  %"n_val" = load i32, i32* %"n"
  %"condtmp" = icmp sle i32 %"i_val", %"n_val"
  br i1 %"condtmp", label %"loopbody", label %"loopend"
loopbody:
  ...
```

#### Optimized LLVM IR (Post-PassBuilder — 6 instructions):
```llvm
define noundef i32 @main() local_unnamed_addr #0 {
entry:
  ret i32 55
}
```

#### Native x86_64 Assembly (`output/05_fibonacci.s`):
```assembly
main:
    movl    $55, %eax
    retq
```

**What happened?**
1. **Mem2Reg:** Stack memory allocations (`alloca`) are converted to SSA register values.
2. **Loop Vectorization & Evaluation:** The compiler detects that the bounds of the loop (`i <= 10`) are statically deterministic.
3. **Constant Folding:** LLVM computes the 10th Fibonacci value (`55`) entirely at compile-time, reducing runtime overhead to a single register load (`movl $55, %eax`).

---

## 🛡️ Error Detection & Safety

Simmer provides multi-phase error reporting with diagnostic messages:

| Category | Trigger Example | Stage Caught | Compiler Output |
|---|---|:---:|---|
| **Lexical Error** | `let x = 10 @ 5` | Lexer | `SyntaxError: Illegal character at position 11: @` |
| **Syntax Error** | `let x 10` | Parser | `SyntaxError: Expected OPERATOR '=', got Token(NUMBER, '10')` |
| **Syntax Error** | `if x > 5 { x = 20` | Parser | `SyntaxError: Expected PUNCTUATION '}', got None` |
| **Semantic Error** | `y = x + 5` *(before let y)* | Semantic | `Semantic Error: Cannot assign to undeclared variable 'y'` |
| **Semantic Error** | `let x = 10; let x = 20` | Semantic | `Semantic Error: Variable 'x' is already declared` |
| **Semantic Error** | `let z = a + 5` *(a undeclared)* | Semantic | `Semantic Error: Using undeclared variable 'a'` |

---

## 🎤 Presentation & Demo Playbook

Follow this script during your review evaluation:

```
[Step 1] Project Introduction:
  "Simmer is an end-to-end DSL compiler featuring a hand-rolled recursive-descent
   frontend and an LLVM optimization and machine-code generation backend."

[Step 2] Live Quick Summary:
  Run: python demo_quick.py
  Point out: 13 benchmark programs passing with 22% to 74% instruction reduction.

[Step 3] Visual AST Inspection:
  Run: python ast_visualizer.py examples/03_while_loop.sim
  Point out: Hierarchical tree showing statements, conditions, and binary operators.

[Step 4] LLVM IR & Assembly Diff:
  Run: python ir_explorer.py examples/05_fibonacci.sim
  Point out: Raw IR with memory loads/stores folding into 'ret i32 55' in assembly.

[Step 5] Safety & Semantic Validation:
  Run: python demo_errors.py
  Point out: Symbol table verifying declarations, preventing undeclared assignments.

[Step 6] Automated Test Verification:
  Run: python test_suite.py
  Point out: 30 automated test cases passing with 100% success rate.
```

---

## 📄 License
This project is developed for educational purposes under the Compiler Design Laboratory curriculum (BCSE307P).
