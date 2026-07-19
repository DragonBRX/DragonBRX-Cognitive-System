import sys
import re

class BRXEInterpreter:
    def __init__(self):
        self.variables = {}
        self.functions = {}
        self.executable_name = "default"

    def run(self, code):
        lines = code.split('\n')
        self.execute_block(lines)

    def execute_block(self, lines):
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Ignore comments and empty lines
            if not line or line.startswith('#'):
                i += 1
                continue

            # Header
            if line.startswith('run '):
                self.executable_name = line.split('"')[1]
                i += 1
                continue

            # Output
            if line.startswith('out '):
                expr = line[4:].strip()
                print(self.evaluate(expr))
                i += 1
                continue

            # Variable Declaration
            if line.startswith('var '):
                # var nome:tipo = valor OR var nome = valor
                match = re.match(r'var\s+(\w+)(?::\w+)?\s*=\s*(.*)', line)
                if match:
                    var_name = match.group(1)
                    value_expr = match.group(2)
                    self.variables[var_name] = self.evaluate(value_expr)
                i += 1
                continue

            # Assignment
            if '=' in line and not line.startswith('var ') and not line.startswith('if ') and not line.startswith('loop '):
                match = re.match(r'(\w+)\s*(=|\+=|-=|\*=|/=)\s*(.*)', line)
                if match:
                    var_name = match.group(1)
                    op = match.group(2)
                    value_expr = match.group(3)
                    val = self.evaluate(value_expr)
                    if op == '=': self.variables[var_name] = val
                    elif op == '+=': self.variables[var_name] += val
                    elif op == '-=': self.variables[var_name] -= val
                    elif op == '*=': self.variables[var_name] *= val
                    elif op == '/=': self.variables[var_name] /= val
                i += 1
                continue

            # Conditionals (Basic implementation)
            if line.startswith('if '):
                condition_expr = line[3:].strip()
                condition = self.evaluate(condition_expr)
                
                # Find else and end
                if_block, else_block, next_i = self.find_if_blocks(lines, i)
                
                if condition:
                    self.execute_block(if_block)
                elif else_block:
                    self.execute_block(else_block)
                
                i = next_i
                continue

            # Loops (Basic Range implementation)
            if line.startswith('loop '):
                # loop i:0 to 10
                match = re.match(r'loop\s+(\w+):(\d+)\s+to\s+(\d+)', line)
                if match:
                    var_name = match.group(1)
                    start = int(match.group(2))
                    end = int(match.group(3))
                    
                    loop_block, next_i = self.find_block_end(lines, i)
                    
                    for val in range(start, end + 1):
                        self.variables[var_name] = val
                        self.execute_block(loop_block)
                    
                    i = next_i
                    continue
                
                # Simple loop N
                match = re.match(r'loop\s+(\d+)', line)
                if match:
                    count = int(match.group(1))
                    loop_block, next_i = self.find_block_end(lines, i)
                    for _ in range(count):
                        self.execute_block(loop_block)
                    i = next_i
                    continue

            i += 1

    def find_block_end(self, lines, start_index):
        block = []
        depth = 1
        i = start_index + 1
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith(('if ', 'loop ', 'func ', 'win ')):
                depth += 1
            elif line == 'end':
                depth -= 1
                if depth == 0:
                    return block, i + 1
            block.append(lines[i])
            i += 1
        return block, i

    def find_if_blocks(self, lines, start_index):
        if_block = []
        else_block = []
        current_block = if_block
        depth = 1
        i = start_index + 1
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith(('if ', 'loop ', 'func ', 'win ')):
                depth += 1
            elif line == 'else' and depth == 1:
                current_block = else_block
                i += 1
                continue
            elif line == 'end':
                depth -= 1
                if depth == 0:
                    return if_block, else_block, i + 1
            current_block.append(lines[i])
            i += 1
        return if_block, else_block, i

    def evaluate(self, expr):
        expr = expr.strip()
        # Handle strings
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]
        # Handle numbers
        if expr.replace('.', '', 1).isdigit():
            return float(expr) if '.' in expr else int(expr)
        # Handle booleans
        if expr == 'true': return True
        if expr == 'false': return False
        # Handle variables
        if expr in self.variables:
            return self.variables[expr]
        
        # Handle built-in functions
        if expr.startswith('str(') and expr.endswith(')'):
            inner = expr[4:-1]
            return str(self.evaluate(inner))

        # Simple arithmetic (very basic for bootstrap)
        if '+' in expr:
            # Handle string concatenation vs addition
            parts = expr.split('+')
            left = self.evaluate(parts[0])
            right = self.evaluate(parts[1])
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            return left + right
        if '-' in expr:
            parts = expr.split('-')
            return self.evaluate(parts[0]) - self.evaluate(parts[1])
        if '>' in expr:
            parts = expr.split('>')
            return self.evaluate(parts[0]) > self.evaluate(parts[1])
        
        return expr

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 brxe_interpreter.py <arquivo.brx>")
        sys.exit(1)
    
    with open(sys.argv[1], 'r') as f:
        code = f.read()
    
    interpreter = BRXEInterpreter()
    interpreter.run(code)
