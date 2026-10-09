from llvmlite import ir

# Create a module to hold compiled code
module = ir.Module(name="simmer_environment_test")

# Define a function: returns 32-bit int, takes two 32-bit ints
i32 = ir.IntType(32)
func_type = ir.FunctionType(i32, (i32, i32))
func = ir.Function(module, func_type, name="add_ingredients")

# Create a basic block of code
block = func.append_basic_block(name="entry")
builder = ir.IRBuilder(block)

# Add addition instructions
arg_a, arg_b = func.args
result = builder.add(arg_a, arg_b, name="sum")
builder.ret(result)

# Print the raw LLVM Intermediate Representation (IR)
print(module)