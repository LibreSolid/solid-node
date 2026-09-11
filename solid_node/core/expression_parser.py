# Copyright (C) 2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Stack-driven scalar parser, including SCAD-local let closures.

Grammar calls yield child parsers to a trampoline. Neither parenthesis depth
nor operator depth consumes Python's call stack. Local names resolve to graph
nodes immediately; let is never a node or a viewer-language extension.
"""

import re

_NUMBER = re.compile(r'(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?')
_NAME = re.compile(r'\$t|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*')
_BINDING = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_OPS = {'==': 10, '!=': 10, '<=': 10, '>=': 10, '<': 10, '>': 10,
        '+': 20, '-': 20, '*': 30, '/': 30, '%': 30, '^': 50}


class Parser:
    def __init__(self, text, interner, error):
        self.text, self.interner, self.error = text, interner, error
        self.i = 0
        self.scopes = []

    def fail(self, message):
        detail = self.text[:200]
        if len(self.text) > 200:
            detail += f'... ({len(self.text)} characters total)'
        raise self.error(f'{message} (offset {self.i} of {detail!r})')

    def space(self):
        while self.i < len(self.text) and self.text[self.i].isspace():
            self.i += 1

    def peek(self):
        self.space()
        return self.text[self.i:self.i + 1]

    def take(self, char):
        if self.peek() != char:
            self.fail(f'expected {char!r}')
        self.i += 1

    def parse(self):
        stack = [self.expr(0)]
        value = None
        while stack:
            try:
                child = stack[-1].send(value)
            except StopIteration as done:
                stack.pop()
                value = done.value
            else:
                stack.append(child)
                value = None
        if self.peek():
            self.fail('unexpected text after a complete expression')
        return value

    def expr(self, minimum):
        left = yield self.prefix()
        while True:
            self.space()
            op = self.text[self.i:self.i + 2]
            if op not in _OPS:
                op = self.text[self.i:self.i + 1]
            precedence = _OPS.get(op, -1)
            if precedence < minimum:
                return left
            self.i += len(op)
            right = yield self.expr(precedence if op == '^' else precedence + 1)
            left = self.interner.compound('binop', op, (left, right))

    def prefix(self):
        char = self.peek()
        if char in ('-', '+'):
            self.i += 1
            # Keep Python's signed numeric spelling as one leaf. A wrapped
            # unary operation such as (-drive) stays an operation node.
            match = _NUMBER.match(self.text, self.i)
            if char == '-' and match:
                self.i = match.end()
                return self.interner.leaf('num', '-' + match.group())
            value = yield self.expr(40)
            return (value if char == '+' else
                    self.interner.compound('unary', '-', (value,)))
        if char == '(':
            self.i += 1
            value = yield self.expr(0)
            self.take(')')
            return value
        match = _NUMBER.match(self.text, self.i)
        if match:
            self.i = match.end()
            return self.interner.leaf('num', match.group())
        match = _NAME.match(self.text, self.i)
        if not match:
            self.fail('expected a scalar expression')
        name = match.group()
        self.i = match.end()
        if self.peek() != '(':
            for scope in reversed(self.scopes):
                if name in scope:
                    return scope[name]
            return self.interner.leaf('name', name)
        self.i += 1
        if name == 'let':
            scope = {}
            self.scopes.append(scope)
            if self.peek() != ')':
                while True:
                    self.space()
                    binding = _BINDING.match(self.text, self.i)
                    if not binding:
                        self.fail('expected a local binding name')
                    self.i = binding.end()
                    self.take('=')
                    value = yield self.expr(0)
                    scope[binding.group()] = value
                    if self.peek() != ',':
                        break
                    self.i += 1
            self.take(')')
            value = yield self.expr(0)
            self.scopes.pop()
            return value
        args = []
        if self.peek() != ')':
            while True:
                args.append((yield self.expr(0)))
                if self.peek() != ',':
                    break
                self.i += 1
        self.take(')')
        return self.interner.compound('call', name, tuple(args))
