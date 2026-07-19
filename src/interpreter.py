import sys
from lexer import Lexer

class BRXInterpreter:
    def __init__(self):
        self.variables = {}
        self.pos = 0
        self.tokens = []

    def error(self, msg):
        token = self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]
        raise SyntaxError(f"Error at {token.line}:{token.column}: {msg}")

    def peek(self, offset=0):
        if self.pos + offset < len(self.tokens):
            return self.tokens[self.pos + offset]
        return None

    def consume(self, expected_type=None, expected_value=None):
        token = self.peek()
        if not token:
            self.error(f"Expected {expected_type or expected_value}, got EOF")
        if expected_type and token.type != expected_type:
            self.error(f"Expected {expected_type}, got {token.type}")
        if expected_value and token.value != expected_value:
            self.error(f"Expected '{expected_value}', got '{token.value}'")
        self.pos += 1
        return token

    def run(self, code):
        lexer = Lexer(code)
        self.tokens = [t for t in lexer.tokenize() if t.type != 'NEWLINE']
        self.pos = 0
        
        # Header mandatory: run "name"
        self.consume('KEYWORD', 'run')
        self.executable_name = self.consume('STRING').value
        
        while self.pos < len(self.tokens):
            self.execute_statement()

    def execute_statement(self):
        token = self.peek()
        if not token: return

        if token.type == 'KEYWORD':
            if token.value == 'var':
                self.handle_var()
            elif token.value == 'out':
                self.handle_out()
            elif token.value == 'if':
                self.handle_if()
            elif token.value == 'loop':
                self.handle_loop()
            elif token.value == 'end':
                self.pos += 1 # end handled by blocks
            else:
                self.pos += 1 # skip unknown keywords for now
        elif token.type == 'ID':
            self.handle_assignment()
        else:
            self.pos += 1

    def handle_var(self):
        self.consume('KEYWORD', 'var')
        token = self.consume()
        if token.type not in ['ID', 'KEYWORD']:
            self.error("Expected variable name")
        name = token.value
        if self.peek() and self.peek().type == 'COLON':
            self.consume('COLON')
            self.consume('KEYWORD') # type (txt, num, etc)
        self.consume('OP_ASSIGN', '=')
        value = self.evaluate_expression()
        self.variables[name] = value

    def handle_assignment(self):
        token = self.consume()
        if token.type not in ['ID', 'KEYWORD']:
            self.error("Expected variable name")
        name = token.value
        op = self.consume('OP_ASSIGN').value
        value = self.evaluate_expression()
        if op == '=': self.variables[name] = value
        elif op == '+=': self.variables[name] += value
        elif op == '-=': self.variables[name] -= value
        elif op == '*=': self.variables[name] *= value
        elif op == '/=': self.variables[name] /= value

    def handle_out(self):
        self.consume('KEYWORD', 'out')
        value = self.evaluate_expression()
        print(value)

    def handle_if(self):
        self.consume('KEYWORD', 'if')
        condition = self.evaluate_expression()
        
        if_body = []
        else_body = []
        current_body = if_body
        depth = 1
        
        while self.pos < len(self.tokens):
            t = self.peek()
            if t.type == 'KEYWORD' and t.value in ['if', 'loop', 'win']: depth += 1
            if t.type == 'KEYWORD' and t.value == 'end':
                depth -= 1
                if depth == 0:
                    self.consume('KEYWORD', 'end')
                    break
            if t.type == 'KEYWORD' and t.value == 'else' and depth == 1:
                current_body = else_body
                self.consume('KEYWORD', 'else')
                continue
            
            current_body.append(self.tokens[self.pos])
            self.pos += 1
            
        if condition:
            self.run_sub_tokens(if_body)
        else:
            self.run_sub_tokens(else_body)

    def handle_loop(self):
        self.consume('KEYWORD', 'loop')
        token = self.peek()
        
        # loop i:0 to 10
        if token.type == 'ID':
            var_name = self.consume('ID').value
            self.consume('COLON')
            start = self.evaluate_expression()
            self.consume('KEYWORD', 'to')
            end = self.evaluate_expression()
            
            loop_body = self.collect_block()
            for i in range(int(start), int(end) + 1):
                self.variables[var_name] = i
                self.run_sub_tokens(loop_body)
        
        # loop N
        elif token.type == 'NUMBER':
            count = self.consume('NUMBER').value
            loop_body = self.collect_block()
            for _ in range(int(count)):
                self.run_sub_tokens(loop_body)

    def collect_block(self):
        block = []
        depth = 1
        while self.pos < len(self.tokens):
            t = self.peek()
            if t.type == 'KEYWORD' and t.value in ['if', 'loop', 'win']: depth += 1
            if t.type == 'KEYWORD' and t.value == 'end':
                depth -= 1
                if depth == 0:
                    self.consume('KEYWORD', 'end')
                    break
            block.append(self.tokens[self.pos])
            self.pos += 1
        return block

    def run_sub_tokens(self, sub_tokens):
        if not sub_tokens: return
        old_tokens = self.tokens
        old_pos = self.pos
        self.tokens = sub_tokens
        self.pos = 0
        while self.pos < len(self.tokens):
            self.execute_statement()
        self.tokens = old_tokens
        self.pos = old_pos

    def evaluate_expression(self):
        # Basic expression evaluator for bootstrap
        left = self.get_primary()
        
        while self.pos < len(self.tokens):
            op = self.peek()
            if op.type in ['OP_ARITH', 'OP_COMP']:
                self.pos += 1
                right = self.get_primary()
                if op.value == '+':
                    if isinstance(left, str) or isinstance(right, str):
                        left = str(left) + str(right)
                    else:
                        left = left + right
                elif op.value == '-': left = left - right
                elif op.value == '*': left = left * right
                elif op.value == '/': left = left / right
                elif op.value == '==': left = (left == right)
                elif op.value == '>': left = (left > right)
                elif op.value == '<': left = (left < right)
            else:
                break
        return left

    def get_primary(self):
        t = self.consume()
        if t.type == 'NUMBER': return t.value
        if t.type == 'STRING': return t.value
        if t.type in ['ID', 'KEYWORD']:
            # Handle str(x) function
            if t.value == 'str' and self.peek() and self.peek().type == 'LPAREN':
                self.consume('LPAREN')
                val = self.evaluate_expression()
                self.consume('RPAREN')
                return str(val)
            # Handle booleans and null
            if t.value == 'true': return True
            if t.value == 'false': return False
            if t.value == 'null': return None
            # Handle variables
            return self.variables.get(t.value, 0)
        self.error(f"Unexpected token in expression: {t}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 interpreter.py <arquivo.brx>")
        sys.exit(1)
    with open(sys.argv[1], 'r') as f:
        code = f.read()
    BRXInterpreter().run(code)
