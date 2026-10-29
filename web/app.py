#!/usr/bin/env python3
"""
Simmer Studio — Web Dashboard Backend (Flask)
==============================================
Provides REST API endpoints for:
  - Code compilation (Lex, Parse, Semantic, Codegen, Optimize, JIT)
  - AST hierarchical JSON serialization
  - Token extraction
  - Instruction metric calculation
  - Example script library
  - In-browser automated test runner
  - Native assembly & object code download

Authors: N. Dheeraj Eshwar & G. Surya Prakash
Course:  BCSE307P — Compiler Design Lab
"""

import sys
import os
import glob
import json
import time
import ctypes
import tempfile
from flask import Flask, render_template, request, jsonify, send_file

# Add parent directory to path to import compiler modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
venv_site = os.path.join(BASE_DIR, "venv", "Lib", "site-packages")

if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from llvmlite import binding as llvm
from lexer import Lexer
from parser_simmer import (
    Parser, Program, Declaration, Assignment, Return,
    BinOp, Number, Identifier, Condition, IfElse, WhileLoop,
    ForLoop, Print
)
from semantic import SemanticAnalyzer
from codegen import CodeGen

# Initialize LLVM backend once
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/favicon.ico')
def favicon():
    fav_ico = os.path.join(os.path.dirname(__file__), "static", "favicon.ico")
    if os.path.exists(fav_ico):
        return send_file(fav_ico, mimetype='image/x-icon')
    fav_path = os.path.join(os.path.dirname(__file__), "static", "favicon.svg")
    return send_file(fav_path, mimetype='image/svg+xml')

# Cache for latest compiled artifacts
LAST_ARTIFACTS = {
    "asm_code": "",
    "obj_bytes": b"",
    "base_name": "simmer_program"
}


def ast_to_dict(node):
    """Recursively converts an AST node into a clean nested JSON structure for tree visualization."""
    if node is None:
        return None
    name = type(node).__name__

    if name == 'Program':
        return {
            'type': 'Program',
            'label': f'Program ({len(node.statements)} stmts)',
            'icon': 'folder',
            'children': [ast_to_dict(s) for s in node.statements]
        }
    elif name == 'Declaration':
        return {
            'type': 'Declaration',
            'label': f'let {node.name} =',
            'badge': node.name,
            'badgeColor': 'blue',
            'icon': 'plus-circle',
            'children': [ast_to_dict(node.value)]
        }
    elif name == 'Assignment':
        return {
            'type': 'Assignment',
            'label': f'{node.name} =',
            'badge': node.name,
            'badgeColor': 'amber',
            'icon': 'edit-3',
            'children': [ast_to_dict(node.value)]
        }
    elif name == 'Return':
        return {
            'type': 'Return',
            'label': 'return',
            'badge': 'exit',
            'badgeColor': 'rose',
            'icon': 'corner-down-left',
            'children': [ast_to_dict(node.value)]
        }
    elif name == 'BinOp':
        return {
            'type': 'BinOp',
            'label': f'Binary Op [{node.op}]',
            'badge': node.op,
            'badgeColor': 'emerald',
            'icon': 'hash',
            'children': [ast_to_dict(node.left), ast_to_dict(node.right)]
        }
    elif name == 'Number':
        return {
            'type': 'Number',
            'label': f'{node.value}',
            'badge': 'number',
            'badgeColor': 'cyan',
            'icon': 'disc',
            'children': []
        }
    elif name == 'Identifier':
        return {
            'type': 'Identifier',
            'label': f'{node.name}',
            'badge': 'var',
            'badgeColor': 'indigo',
            'icon': 'tag',
            'children': []
        }
    elif name == 'Condition':
        return {
            'type': 'Condition',
            'label': f'Condition [{node.op}]',
            'badge': node.op,
            'badgeColor': 'purple',
            'icon': 'help-circle',
            'children': [ast_to_dict(node.left), ast_to_dict(node.right)]
        }
    elif name == 'IfElse':
        children = [
            {'type': 'Branch', 'label': 'Condition', 'badge': 'if', 'badgeColor': 'purple', 'children': [ast_to_dict(node.condition)]},
            {'type': 'Branch', 'label': f'Then ({len(node.then_body)} stmts)', 'badge': 'then', 'badgeColor': 'emerald', 'children': [ast_to_dict(s) for s in node.then_body]}
        ]
        if node.else_body:
            children.append({'type': 'Branch', 'label': f'Else ({len(node.else_body)} stmts)', 'badge': 'else', 'badgeColor': 'amber', 'children': [ast_to_dict(s) for s in node.else_body]})
        return {
            'type': 'IfElse',
            'label': 'if ... else',
            'badge': 'branch',
            'badgeColor': 'purple',
            'icon': 'git-branch',
            'children': children
        }
    elif name == 'WhileLoop':
        return {
            'type': 'WhileLoop',
            'label': 'while loop',
            'badge': 'loop',
            'badgeColor': 'teal',
            'icon': 'repeat',
            'children': [
                {'type': 'Branch', 'label': 'Condition', 'badge': 'cond', 'badgeColor': 'purple', 'children': [ast_to_dict(node.condition)]},
                {'type': 'Branch', 'label': f'Body ({len(node.body)} stmts)', 'badge': 'body', 'badgeColor': 'teal', 'children': [ast_to_dict(s) for s in node.body]}
            ]
        }
    elif name == 'ForLoop':
        return {
            'type': 'ForLoop',
            'label': f'for {node.var_name}',
            'badge': node.var_name,
            'badgeColor': 'teal',
            'icon': 'refresh-cw',
            'children': [
                {'type': 'Branch', 'label': 'Start', 'badge': 'from', 'badgeColor': 'cyan', 'children': [ast_to_dict(node.start)]},
                {'type': 'Branch', 'label': 'End', 'badge': 'to', 'badgeColor': 'cyan', 'children': [ast_to_dict(node.end)]},
                {'type': 'Branch', 'label': f'Body ({len(node.body)} stmts)', 'badge': 'body', 'badgeColor': 'teal', 'children': [ast_to_dict(s) for s in node.body]}
            ]
        }
    elif name == 'Print':
        return {
            'type': 'Print',
            'label': 'print',
            'badge': 'io',
            'badgeColor': 'sky',
            'icon': 'terminal',
            'children': [ast_to_dict(node.value)]
        }
    return {'type': name, 'label': str(node), 'children': []}


def capture_jit_execution(engine):
    """
    Executes the JIT main function, capturing both return value and CRT printf output.
    """
    func_ptr = engine.get_function_address("main")
    cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(func_ptr)

    captured_text = ""
    # Attempt C runtime stdout redirect for Windows Universal CRT
    try:
        sys.stdout.flush()
        temp_fd, temp_path = tempfile.mkstemp()
        old_stdout = os.dup(1)
        os.dup2(temp_fd, 1)

        result = cfunc()

        # Flush CRT / libc buffer
        try:
            ctypes.CDLL('ucrtbase.dll').fflush(None)
        except Exception:
            try:
                ctypes.cdll.msvcrt.fflush(None)
            except Exception:
                try:
                    # Linux/glibc: fflush(NULL) flushes all open stdio streams
                    ctypes.CDLL(None).fflush(None)
                except Exception:
                    pass

        sys.stdout.flush()
        os.dup2(old_stdout, 1)
        os.close(old_stdout)
        os.close(temp_fd)

        with open(temp_path, 'r', encoding='utf-8', errors='replace') as f:
            captured_text = f.read()
        try:
            os.remove(temp_path)
        except Exception:
            pass
    except Exception:
        result = cfunc()
        captured_text = ""

    return result, captured_text.strip()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/compile', methods=['POST'])
def compile_code():
    data = request.get_json() or {}
    source_code = data.get('code', '')
    raw_opt = str(data.get('opt_level', 3)).upper().replace('-O', '').replace('O', '').strip()
    try:
        opt_level = int(raw_opt)
    except (ValueError, TypeError):
        opt_level = 3
    opt_level = max(0, min(3, opt_level))
    base_name = data.get('name', 'simmer_program')

    t0 = time.time()
    response = {
        'success': False,
        'stages': [],
        'error': None,
        'error_stage': None
    }

    try:
        # Phase 1: Lexical Analysis
        p1_start = time.time()
        lexer = Lexer()
        raw_tokens = lexer.tokenize(source_code)
        tokens_list = [
            {'type': tok.type, 'value': tok.value}
            for tok in raw_tokens
        ]
        response['stages'].append({
            'name': 'Lexer',
            'status': 'passed',
            'time_ms': round((time.time() - p1_start) * 1000, 2),
            'summary': f'{len(tokens_list)} tokens generated'
        })
        response['tokens'] = tokens_list

        # Phase 2: Parsing (AST Construction)
        p2_start = time.time()
        parser = Parser(raw_tokens)
        ast = parser.parse()
        ast_dict = ast_to_dict(ast)
        ast_str = "\n".join([str(stmt) for stmt in ast.statements])
        response['stages'].append({
            'name': 'Parser',
            'status': 'passed',
            'time_ms': round((time.time() - p2_start) * 1000, 2),
            'summary': f'{len(ast.statements)} top-level statements'
        })
        response['ast_tree'] = ast_dict
        response['ast_raw'] = ast_str

        # Phase 3: Semantic Analysis
        p3_start = time.time()
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)
        symbols = sorted(list(analyzer.symbol_table))
        response['stages'].append({
            'name': 'Semantic Analyzer',
            'status': 'passed',
            'time_ms': round((time.time() - p3_start) * 1000, 2),
            'summary': f'Validated {len(symbols)} variables'
        })
        response['symbols'] = symbols

        # Phase 4: Code Generation (LLVM IR)
        p4_start = time.time()
        codegen = CodeGen()
        codegen.generate(ast)
        raw_ir = str(codegen.module)
        response['stages'].append({
            'name': 'LLVM Codegen',
            'status': 'passed',
            'time_ms': round((time.time() - p4_start) * 1000, 2),
            'summary': 'Raw LLVM IR generated'
        })
        response['raw_ir'] = raw_ir

        # Phase 5: PassBuilder Optimization
        p5_start = time.time()
        parsed_module = llvm.parse_assembly(raw_ir)
        parsed_module.verify()

        target = llvm.Target.from_default_triple()
        target_machine = target.create_target_machine()

        if opt_level > 0:
            pto = llvm.create_pipeline_tuning_options(speed_level=opt_level)
            pass_builder = llvm.create_pass_builder(target_machine, pto)
            pass_manager = pass_builder.getModulePassManager()
            pass_manager.run(parsed_module, pass_builder)
            optimized_ir = str(parsed_module)
        else:
            optimized_ir = raw_ir

        before_instr = len([l for l in raw_ir.split('\n') if '=' in l or 'ret' in l])
        after_instr = len([l for l in optimized_ir.split('\n') if '=' in l or 'ret' in l])
        eliminated = before_instr - after_instr
        pct_reduction = round((eliminated / before_instr * 100), 1) if before_instr > 0 else 0

        response['stages'].append({
            'name': f'Optimizer (-O{opt_level})',
            'status': 'passed',
            'time_ms': round((time.time() - p5_start) * 1000, 2),
            'summary': f'{eliminated} redundant instructions removed ({pct_reduction}%)'
        })
        response['optimized_ir'] = optimized_ir
        response['metrics'] = {
            'before': before_instr,
            'after': after_instr,
            'eliminated': eliminated,
            'reduction_pct': pct_reduction,
            'opt_level': opt_level
        }

        # Phase 6: JIT Execution
        p6_start = time.time()
        engine = llvm.create_mcjit_compiler(parsed_module, target_machine)
        engine.finalize_object()
        engine.run_static_constructors()

        jit_result, stdout_output = capture_jit_execution(engine)

        response['stages'].append({
            'name': 'JIT Engine',
            'status': 'passed',
            'time_ms': round((time.time() - p6_start) * 1000, 2),
            'summary': f'Exited with code {jit_result}'
        })
        response['jit_result'] = jit_result
        response['stdout'] = stdout_output

        # Phase 7: Assembly & Machine Object Emission
        p7_start = time.time()
        asm_code = target_machine.emit_assembly(parsed_module)
        obj_code = target_machine.emit_object(parsed_module)

        LAST_ARTIFACTS['asm_code'] = asm_code
        LAST_ARTIFACTS['obj_bytes'] = obj_code
        LAST_ARTIFACTS['base_name'] = base_name

        response['stages'].append({
            'name': 'Native Emission',
            'status': 'passed',
            'time_ms': round((time.time() - p7_start) * 1000, 2),
            'summary': 'Assembly (.s) and Object (.o) compiled'
        })
        response['asm_code'] = asm_code
        response['target_triple'] = llvm.get_default_triple()
        response['total_time_ms'] = round((time.time() - t0) * 1000, 2)
        response['success'] = True

    except SyntaxError as e:
        response['success'] = False
        response['error'] = str(e)
        response['error_stage'] = 'Syntax / Lexer / Parser Error'
    except Exception as e:
        response['success'] = False
        response['error'] = str(e)
        msg = str(e)
        if 'Semantic Error' in msg:
            response['error_stage'] = 'Semantic Error'
        else:
            response['error_stage'] = 'Compilation Error'

    return jsonify(response)


@app.route('/api/examples', methods=['GET'])
def get_examples():
    """Returns all 13 verified benchmark scripts with titles and descriptions."""
    examples_dir = os.path.join(BASE_DIR, "examples")
    sim_files = sorted(glob.glob(os.path.join(examples_dir, "*.sim")))

    examples = []
    for filepath in sim_files:
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()

        # Extract title from first line comment
        lines = code.strip().split('\n')
        title = filename
        if lines and lines[0].startswith('//'):
            title = lines[0].replace('//', '').strip()

        examples.append({
            'filename': filename,
            'title': title,
            'code': code
        })

    return jsonify(examples)


@app.route('/api/run-tests', methods=['POST'])
def run_tests():
    """Runs the 30-case test suite and returns individual test statuses."""
    from test_suite import TESTS, compile_and_run

    results = []
    passed = 0
    failed = 0

    for name, code, expected in TESTS:
        t0 = time.time()
        try:
            actual = compile_and_run(code)
            is_pass = (actual == expected)
            if is_pass:
                passed += 1
            else:
                failed += 1
            results.append({
                'name': name,
                'status': 'pass' if is_pass else 'fail',
                'expected': expected,
                'actual': actual,
                'time_ms': round((time.time() - t0) * 1000, 2)
            })
        except Exception as e:
            failed += 1
            results.append({
                'name': name,
                'status': 'error',
                'expected': expected,
                'actual': str(e),
                'time_ms': round((time.time() - t0) * 1000, 2)
            })

    return jsonify({
        'total': len(TESTS),
        'passed': passed,
        'failed': failed,
        'results': results
    })


@app.route('/api/download/asm', methods=['GET'])
def download_asm():
    if not LAST_ARTIFACTS['asm_code']:
        return "No assembly generated yet.", 400
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".s", mode="w", encoding="utf-8")
    temp.write(LAST_ARTIFACTS['asm_code'])
    temp.close()
    return send_file(temp.name, as_attachment=True, download_name=f"{LAST_ARTIFACTS['base_name']}.s")


@app.route('/api/download/obj', methods=['GET'])
def download_obj():
    if not LAST_ARTIFACTS['obj_bytes']:
        return "No object code generated yet.", 400
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".o", mode="wb")
    temp.write(LAST_ARTIFACTS['obj_bytes'])
    temp.close()
    return send_file(temp.name, as_attachment=True, download_name=f"{LAST_ARTIFACTS['base_name']}.o")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"\n* Simmer Studio Backend active on http://127.0.0.1:{port}\n")
    app.run(host='127.0.0.1', port=port, debug=False)

