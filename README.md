# 🍲 Simmer Compiler

A custom-built toy compiler translating high-level source scripts into native machine code. Simmer features a hand-rolled frontend (Lexer & Parser) and a powerful production-grade LLVM backend. 

Built for a Compiler Design Lab project.

## 🚀 Features

* **Custom Frontend:** 100% hand-rolled recursive-descent parser and lexical analyzer built from scratch.
* **Semantic Analysis:** Validates variable scope, assignments, and type checks.
* **LLVM Code Generation:** Transforms the validated Abstract Syntax Tree (AST) into raw LLVM Intermediate Representation (IR).
* **Optimization Pipeline:** Utilizes modern LLVM PassBuilder for constant folding and dead code elimination to shrink instruction counts.
* **JIT & AOT Execution:** Just-In-Time (JIT) executes code instantly in memory, and Ahead-Of-Time (AOT) emits native assembly (`.s`) and machine object code (`.o`).

## 🛠️ Tech Stack

* **Language:** Python
* **Backend:** [llvmlite](https://llvmlite.readthedocs.io/en/latest/) (LLVM binding for Python)
* **Architecture:** Lexer -> Parser -> Semantic Analyzer -> LLVM IR Gen -> Optimizer -> Native Code Gen

## 💻 Usage

Simmer includes a command-line interface to compile and execute `.sim` scripts in one seamless step.

### 1. Installation
Install the required LLVM bindings:
```bash
pip install llvmlite
```

### 2. Example Script (`simmer_example.sim`)
```swift
let volume = 100
let time = 0

while volume > 50 {
    volume = volume - 10
    time = time + 1
}

return time
```

### 3. Compiling & Running
Run the compiler from your terminal:
```bash
python simmer.py simmer_example.sim
```

### Expected Output
The compiler will lex, parse, generate IR, optimize, execute, and emit the binaries:
```text
--- Compiling simmer_example.sim ---

--- OPTIMIZATION METRICS ---
Instructions before: 13
Instructions after:  6
Efficiency Gain:     7 redundant instructions eliminated!

--- JIT EXECUTION ---
Program exited with code: 5

--- DISK EMISSION ---
-> Saved native assembly to 'simmer_example.s'
-> Saved machine object code to 'simmer_example.o'

COMPILER PIPELINE COMPLETE.
```

## 📚 Authors
* **N. Dheeraj Eshwar**
* **G. Surya Prakash**

Designed for Compiler Design Lab.
