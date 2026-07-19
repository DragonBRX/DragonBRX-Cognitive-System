import sys
from lexer import Lexer
from visual import BRXVEngine
import time

class BRXInterpreter:
    def __init__(self):
        self.variables = {}
        self.pos = 0
        self.tokens = []
        self.visual = BRXVEngine()
        self.current_win_props = {}

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
            elif token.value == 'win':
                self.handle_win()
            elif token.value == 'upd':
                self.visual.update_sprites()
                self.pos += 1
            elif token.value == 'drw':
                self.visual.render()
                self.pos += 1
            elif token.value == 'wait':
                self.pos += 1
                ms = self.evaluate_expression()
                time.sleep(ms / 1000.0)
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

    def handle_win(self):
        self.consume('KEYWORD', 'win')
        props = {'sz': '800x600', 'tt': 'BRX Window', 'bg': '#1a1a2e'}
        
        while self.pos < len(self.tokens):
            t = self.peek()
            if t.type == 'KEYWORD' and t.value == 'end':
                self.consume('KEYWORD', 'end')
                break
            
            if t.type == 'KEYWORD':
                if t.value == 'sz':
                    self.consume('KEYWORD')
                    props['sz'] = self.consume().value
                elif t.value == 'tt':
                    self.consume('KEYWORD')
                    props['tt'] = self.consume().value
                elif t.value == 'bg':
                    self.consume('KEYWORD')
                    props['bg'] = self.consume().value
                elif t.value == 'txt':
                    self.handle_win_txt()
                elif t.value == 'btn':
                    self.handle_win_btn()
                elif t.value == 'spr':
                    self.handle_win_spr()
                elif t.value == 'rect':
                    self.handle_win_rect()
                else:
                    self.pos += 1
            else:
                self.pos += 1
        
        w, h = map(int, props['sz'].split('x'))
        self.visual.init_window(w, h, props['tt'], props['bg'])

    def handle_win_txt(self):
        self.consume('KEYWORD', 'txt')
        text = self.evaluate_expression()
        opts = self.parse_opts()
        self.visual.add_text(text, opts.get('x', 0), opts.get('y', 0), opts.get('sz', 16), opts.get('col', '#FFFFFF'))

    def handle_win_btn(self):
        self.consume('KEYWORD', 'btn')
        text = self.evaluate_expression()
        opts = self.parse_opts()
        # For bootstrap, button callback is simple cls
        self.visual.add_button(text, opts.get('x', 0), opts.get('y', 0), opts.get('w', 80), opts.get('h', 30), self.visual.on_close)
        # Skip until end of btn block
        while self.pos < len(self.tokens):
            if self.peek().value == 'end':
                self.consume('KEYWORD', 'end')
                break
            self.pos += 1

    def handle_win_spr(self):
        self.consume('KEYWORD', 'spr')
        path = self.evaluate_expression()
        opts = self.parse_opts()
        sprite = self.visual.add_sprite(path, opts.get('x', 0), opts.get('y', 0), opts.get('w', 40), opts.get('h', 40), opts.get('col', '#FF0000'))
        
        # Check for vel sub-block
        while self.pos < len(self.tokens):
            t = self.peek()
            if t.value == 'end':
                self.consume('KEYWORD', 'end')
                break
            if t.value == 'vel':
                self.consume('KEYWORD')
                vopts = self.parse_opts()
                sprite['vx'] = vopts.get('x', 0)
                sprite['vy'] = vopts.get('y', 0)
            else:
                self.pos += 1

    def handle_win_rect(self):
        self.consume('KEYWORD', 'rect')
        opts = self.parse_opts()
        self.visual.add_rect(opts.get('x', 0), opts.get('y', 0), opts.get('w', 100), opts.get('h', 100), opts.get('col', '#FFFFFF'))

    def parse_opts(self):
        opts = {}
        while self.pos < len(self.tokens):
            t = self.peek()
            if t.type == 'KEYWORD' and t.value in ['x', 'y', 'z', 'sz', 'col', 'w', 'h', 'vel']:
                key = self.consume().value
                self.consume('COLON')
                val = self.evaluate_expression()
                opts[key] = val
            else:
                break
        return opts

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
        
        # loop while win.open
        if token.value == 'while':
            self.consume('KEYWORD', 'while')
            cond_tokens = []
            # Peek until we find a newline or block start equivalent
            # For bootstrap, we assume loop while win.open
            expr_str = ""
            while self.peek().type != 'NEWLINE' and self.peek().value not in ['upd', 'drw', 'wait', 'out', 'var', 'if', 'loop']:
                t = self.consume()
                expr_str += str(t.value)
            
            loop_body = self.collect_block()
            
            # Simple simulation for loop while win.open
            if "win.open" in expr_str:
                while self.visual.is_open:
                    self.run_sub_tokens(loop_body)
            return

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
