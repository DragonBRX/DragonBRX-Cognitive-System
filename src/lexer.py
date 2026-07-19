import re

class Token:
    def __init__(self, type, value, line, column):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, {self.line}:{self.column})"

class Lexer:
    TOKEN_SPEC = [
        ('COMMENT',   r'#.*'),
        ('STRING',    r'"[^"]*"'),
        ('NUMBER',    r'\d+(\.\d+)?'),
        ('KEYWORD',   r'\b(run|var|if|else|end|loop|while|forever|to|step|break|continue|func|return|out|in|true|false|null|win|bin|hw|sbx|tr|txt|num|bool|list|btn|spr|rect|sz|tt|bg|x|y|z|vel|ang|col|clk|cls|upd|drw|wait|opt|tgt|mem|alloc|free|reg|set|lim|load|src|map)\b'),
        ('ID',        r'[a-zA-Z_][a-zA-Z0-9_]*'),
        ('OP_ASSIGN', r'[+\-*/%]?='),
        ('OP_COMP',   r'==|!=|<=|>=|<|>'),
        ('OP_ARITH',  r'[+\-*/%]'),
        ('LPAREN',    r'\('),
        ('RPAREN',    r'\)'),
        ('LBRACKET',  r'\['),
        ('RBRACKET',  r'\]'),
        ('COLON',     r':'),
        ('COMMA',     r','),
        ('ARROW',     r'->'),
        ('NEWLINE',   r'\n'),
        ('SKIP',      r'[ \t]+'),
        ('MISMATCH',  r'.'),
    ]

    def __init__(self, code):
        self.code = code
        self.tokens = []

    def tokenize(self):
        line_num = 1
        line_start = 0
        regex = '|'.join('(?P<%s>%s)' % pair for pair in self.TOKEN_SPEC)
        for mo in re.finditer(regex, self.code):
            kind = mo.lastgroup
            value = mo.group()
            column = mo.start() - line_start
            if kind == 'NEWLINE':
                line_start = mo.end()
                line_num += 1
                self.tokens.append(Token('NEWLINE', '\n', line_num, column))
            elif kind == 'SKIP' or kind == 'COMMENT':
                pass
            elif kind == 'MISMATCH':
                raise SyntaxError(f'Unexpected character {value!r} at line {line_num}')
            else:
                if kind == 'STRING':
                    value = value[1:-1]
                elif kind == 'NUMBER':
                    value = float(value) if '.' in value else int(value)
                self.tokens.append(Token(kind, value, line_num, column))
        return self.tokens
