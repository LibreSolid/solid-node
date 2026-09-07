# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The expression language the framework emits: a reader, not a new one.

Every symbolic value in the framework is a solid2 `OpenSCADConstant`, and
`OpenSCADConstant` is string-eager (design.md, Context): the text IS the
value, built once per use rather than once per distinct subexpression. This
module does not change that -- it reads the text the producer already built,
so a document can publish each distinct subexpression once (ADR-080).

The grammar (design.md D2) is exactly what two producers emit:

- `OpenSCADConstant.__operator_base__` / `__roperator_base__`:
  ``f'({self} {op} {other})'`` for `+ - * / % ^ == != < > <= >=`.
- `OpenSCADConstant.__unary_operator_base__`: ``f'({op}{self})'``, `op`
  always `-`.
- `OpenSCADConstant.__abs__`: ``f'abs({self})'``.
- `solid_node.math._symbolic_call`: ``f'{name}({rendered})'``, `rendered`
  being its arguments joined by `', '`.
- `$t`, a bare driver id, a dotted one, and a plain number in every form
  `str()` of a Python number produces, exponent notation included.

solid2 fully parenthesises every operation it builds, so precedence is never
load-bearing in text the framework produced -- but a hand-written
`scad_inline` string is free to omit the parentheses, so this parser
implements real precedence climbing rather than leaning on them.

Nothing here is a new expression language: every name and operator it can
read is one the two producers above already emit. `solid_node/core/expressions.py`
is a framework-internal reader, never a public interface (tasks.md 5.4).

An expression this parser cannot read is not a framework failure -- see
`bind_expressions`: it is published verbatim and unshared, with a warning,
and the caller decides nothing changes about the build.
"""

import logging
import re


logger = logging.getLogger('core.expressions')

#: Kinds a node take. 'num' and 'name' are leaves; the rest are compound.
_LEAF_KINDS = ('num', 'name')

_NUMBER_RE = re.compile(r'(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?')
_NAME_RE = re.compile(r'\$t|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*')
_COMPARISON_OPS = ('==', '!=', '<=', '>=', '<', '>')

#: How much of an unreadable expression a warning names -- a published
#: expression may be megabytes, and the offending text is diagnostic, not
#: the whole document restated.
_WARNING_TRUNCATION = 200


class ExpressionError(ValueError):
    """Text that is not in the language the two producers emit.

    Never raised for text that publishes and renders today: solid2's own
    output always parses. This is raised only for a `scad_inline` string,
    or otherwise hand-built text, outside that language -- and the caller
    (`bind_expressions`) catches it, publishing the offending expression
    verbatim and unshared rather than failing the build.
    """


class BindingTableError(ValueError):
    """A bindings table the producer would publish is wrong.

    Always a framework defect, never a project's fault (design.md D2):
    an entry naming a later entry, a name colliding with a declared
    driver id, or a rewrite that does not reproduce what the producer
    built. Raising here means the document is not written at all.
    """


class Node:
    """One structurally-interned expression node.

    `kind` is one of `'num'`, `'name'` (leaves, carrying their own literal
    `text`) or `'unary'`, `'binop'`, `'call'` (compound, carrying `children`
    and an `op` -- the operator symbol or the called name). Interning makes
    identity equality structural equality: two parses of equal structure
    return the SAME `Node` object, which is what lets occurrence counting
    and the round-trip test (tasks.md 1.4) use `is`.
    """

    __slots__ = ('id', 'kind', 'op', 'children', 'text')

    def __init__(self, id, kind, op=None, children=(), text=None):
        self.id = id
        self.kind = kind
        self.op = op
        self.children = children
        self.text = text

    def __repr__(self):
        if self.kind in _LEAF_KINDS:
            return f'<Node {self.kind} {self.text!r}>'
        return f'<Node {self.kind} {self.op!r} x{len(self.children)}>'


class Interner:
    """The structural table: one canonical `Node` per `(kind, op, child
    ids)`, and how many times each was returned.

    `order` is creation order. A compound node is only created once its
    children already exist, so `order` is a topological order -- a child
    always precedes its parents -- which is what lets the bindings table be
    built by a single pass over it (design.md D5).
    """

    def __init__(self):
        self._table = {}
        self.order = []
        self.counts = {}

    def leaf(self, kind, text):
        key = (kind, text)
        node = self._table.get(key)
        if node is None:
            node = Node(len(self.order), kind, op=text, text=text)
            self._table[key] = node
            self.order.append(node)
        self.touch(node)
        return node

    def compound(self, kind, op, children):
        key = (kind, op, tuple(child.id for child in children))
        node = self._table.get(key)
        if node is None:
            node = Node(len(self.order), kind, op=op, children=children)
            self._table[key] = node
            self.order.append(node)
        self.touch(node)
        return node

    def touch(self, node):
        """Record one more use of `node` -- including its own creation,
        which is the first use. `(big * big)` uses `big` twice even though
        nothing else ever will (design.md D5: "occurrences, not distinct
        parents")."""
        self.counts[node] = self.counts.get(node, 0) + 1


def _matching_paren(text, open_pos):
    depth = 0
    i = open_pos
    n = len(text)
    while i < n:
        char = text[i]
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ExpressionError(
        f'unbalanced parenthesis in {_truncate(text)!r}')


class _Parser:
    """One recursive-descent, precedence-climbing pass over `text`.

    No separate tokenizing pass: each grammar rule reads directly off
    `text[self.i:]`, which is what lets `_parenthesised` capture a group's
    exact source substring for the memo (design.md D2, "Speed comes from a
    substring memo") before deciding whether to parse it at all.
    """

    def __init__(self, text, interner, memo=None):
        self.text = text
        self.interner = interner
        self.memo = memo
        self.i = 0
        self.n = len(text)

    def parse(self):
        node = self._expr()
        self._skip_ws()
        if self.i != self.n:
            raise self._error('unexpected text after a complete expression')
        return node

    # -------- errors and lexical helpers --------

    def _error(self, message):
        return ExpressionError(
            f'{message} (offset {self.i} of {_truncate(self.text)!r})')

    def _skip_ws(self):
        while self.i < self.n and self.text[self.i] in ' \t\n\r':
            self.i += 1

    def _peek(self):
        return self.text[self.i] if self.i < self.n else ''

    def _starts_with(self, token):
        return self.text.startswith(token, self.i)

    # -------- grammar, loosest to tightest --------

    def _expr(self):
        return self._comparison()

    def _comparison(self):
        self._skip_ws()
        left = self._additive()
        self._skip_ws()
        for op in _COMPARISON_OPS:
            if self._starts_with(op):
                self.i += len(op)
                self._skip_ws()
                right = self._additive()
                return self.interner.compound('binop', op, (left, right))
        return left

    def _additive(self):
        self._skip_ws()
        left = self._multiplicative()
        while True:
            self._skip_ws()
            char = self._peek()
            if char not in ('+', '-'):
                break
            self.i += 1
            self._skip_ws()
            right = self._multiplicative()
            left = self.interner.compound('binop', char, (left, right))
        return left

    def _multiplicative(self):
        self._skip_ws()
        left = self._unary()
        while True:
            self._skip_ws()
            char = self._peek()
            if char not in ('*', '/', '%'):
                break
            self.i += 1
            self._skip_ws()
            right = self._unary()
            left = self.interner.compound('binop', char, (left, right))
        return left

    def _unary(self):
        self._skip_ws()
        if self._peek() == '-':
            minus_pos = self.i
            self.i += 1
            # A bare negative-number literal is one token in the text --
            # Python's str() of a negative number, never the unary-operator
            # wrap, which is always parenthesised (design.md D2). Only
            # merge when the digits are RIGHT there, no whitespace between:
            # "(5 - -3)"'s second '-' merges, its first (surrounded by
            # spaces, the binary operator) never reaches this rule at all.
            match = (_NUMBER_RE.match(self.text, self.i)
                     if self.i < self.n
                     and (self.text[self.i].isdigit() or self.text[self.i] == '.')
                     else None)
            if match is not None:
                literal = self.text[minus_pos:match.end()]
                self.i = match.end()
                return self.interner.leaf('num', literal)
            operand = self._unary()
            return self.interner.compound('unary', '-', (operand,))
        if self._peek() == '+':
            # Never emitted by either producer; harmless to accept as a
            # no-op the way OpenSCAD's own grammar would.
            self.i += 1
            return self._unary()
        return self._power()

    def _power(self):
        base = self._atom()
        self._skip_ws()
        if self._peek() == '^':
            self.i += 1
            self._skip_ws()
            exponent = self._unary()
            return self.interner.compound('binop', '^', (base, exponent))
        return base

    def _atom(self):
        self._skip_ws()
        if self.i >= self.n:
            raise self._error('expected an expression')
        char = self.text[self.i]
        if char == '(':
            return self._parenthesised()
        match = _NUMBER_RE.match(self.text, self.i)
        if match is not None:
            literal = match.group()
            self.i = match.end()
            return self.interner.leaf('num', literal)
        match = _NAME_RE.match(self.text, self.i)
        if match is not None:
            name = match.group()
            self.i = match.end()
            self._skip_ws()
            if self._peek() == '(':
                return self._call(name)
            return self.interner.leaf('name', name)
        raise self._error(f'unexpected character {char!r}')

    def _call(self, name):
        # self.i is at the '(' following `name`.
        self.i += 1
        args = []
        self._skip_ws()
        if self._peek() != ')':
            args.append(self._expr())
            self._skip_ws()
            while self._peek() == ',':
                self.i += 1
                self._skip_ws()
                args.append(self._expr())
                self._skip_ws()
        if self._peek() != ')':
            raise self._error(f"expected ')' to close the call to {name!r}")
        self.i += 1
        return self.interner.compound('call', name, tuple(args))

    def _parenthesised(self):
        open_pos = self.i
        close = _matching_paren(self.text, open_pos)
        inner = self.text[open_pos + 1:close]
        if self.memo is not None:
            cached = self.memo.get(inner)
            if cached is not None:
                self.interner.touch(cached)
                self.i = close + 1
                return cached
        # Parsed in place, on THIS parser, rather than handing `inner` to a
        # fresh `_Parser(...).parse()`: a chain of nested groups -- the
        # shape solid2 itself builds, each level its own parenthesised
        # group -- then costs one grammar descent's worth of stack frames
        # per level instead of one plus a wrapper `parse()` call, raising
        # (not removing) how deep a document can reach before
        # `bind_expressions` falls back to its `RecursionError` handling.
        self.i = open_pos + 1
        node = self._expr()
        self._skip_ws()
        if self.i != close:
            raise self._error(
                "unexpected text before the closing parenthesis")
        if self.memo is not None:
            self.memo[inner] = node
        self.i = close + 1
        return node


def parse(text, interner=None, memo=None):
    """Parse `text` into an interned `Node`.

    `interner` defaults to a fresh one; pass a shared `Interner` to build
    document-wide sharing across several calls. `memo`, when a dict, is the
    substring shortcut for parenthesised groups (design.md D2) and should be
    shared across every `parse()` call over one document so a repeated
    group is skipped rather than re-parsed; pass `None` (the default) to
    disable it -- the answer is identical either way (tasks.md 1.3), only
    slower.

    Raises `ExpressionError` on anything outside the grammar; never
    guesses.
    """
    if interner is None:
        interner = Interner()
    return _Parser(text, interner, memo).parse()


# `render`, `_matches`, `_name_leaves` and `_has_named_descendant` below
# each recurse ONE stack frame per level of a node's own tree -- unlike the
# parser, which spends several frames (`_expr` down through `_atom`) per
# level of SOURCE TEXT nesting. A node these functions are ever handed
# came from a `parse()` call that already completed inside Python's
# recursion limit at that higher per-level cost, so its tree cannot be
# deeper than that call's own recursion allowed, and a strictly cheaper
# per-level traversal of the same tree cannot exceed the limit either.
# `bind_expressions`'s `RecursionError` handling is what keeps a node THAT
# deep from ever reaching these functions in the first place.


def _publish(node, names):
    name = names.get(node)
    if name is not None:
        return name
    return render(node, names)


def render(node, names=None):
    """The canonical text for `node`.

    A leaf renders its own literal text, verbatim. A compound node
    reconstructs the producer's own format -- `(A op B)`, `(-A)`,
    `name(A, B)` -- from its children, substituting `names[child]` for any
    child that is itself a bound reference (`names`, when given, maps a
    `Node` to the name it was minted under). With no `names` this is a full
    expansion: `parse(render(node)) is node` when re-parsed into the same
    interner (tasks.md 1.4), because the text is exactly what the producer
    would have written before anything was shared.
    """
    names = names or {}
    if node.kind in _LEAF_KINDS:
        return node.text
    if node.kind == 'unary':
        return f'(-{_publish(node.children[0], names)})'
    if node.kind == 'binop':
        left = _publish(node.children[0], names)
        right = _publish(node.children[1], names)
        return f'({left} {node.op} {right})'
    if node.kind == 'call':
        args = ', '.join(_publish(child, names) for child in node.children)
        return f'{node.op}({args})'
    raise AssertionError(f'unknown node kind {node.kind!r}')  # pragma: no cover


def _truncate(text, limit=_WARNING_TRUNCATION):
    if len(text) <= limit:
        return text
    return f'{text[:limit]}... ({len(text)} characters total)'


def _is_bindable(node):
    """Every shared node except a bare number or a bare name (design.md
    D5): a reference costs four characters, and a literal or a driver id is
    shorter written out than referenced."""
    return node.kind not in _LEAF_KINDS


def _mint_prefix(driver_ids):
    """The prefix `_mint_names` mints under: `_b`, lengthened by a leading
    underscore for as long as some declared driver id matches
    `<prefix>\\d+` (design.md D4). Returned separately from the names
    themselves so a caller -- `_validate_bindings` -- can recognise a
    MINTED-LOOKING name without re-deriving the prefix from the table."""
    prefix = '_b'
    while True:
        pattern = re.compile(r'\A' + re.escape(prefix) + r'\d+\Z')
        if not any(pattern.match(identifier) for identifier in driver_ids):
            return prefix
        prefix = '_' + prefix


def _mint_names(shared_nodes, prefix):
    """`_b0`, `_b1`, ... in table order, under `prefix` (design.md D4)."""
    return {node: f'{prefix}{index}' for index, node in enumerate(shared_nodes)}


def _bindings_list(shared_nodes, names):
    """The ordered table: each entry's own text, built with only the
    names minted before it visible -- which is what makes an entry name
    only $t, a driver id, or an earlier entry (design.md D3)."""
    entries = []
    visible = {}
    for node in shared_nodes:
        entries.append({'name': names[node], 'expression': render(node, visible)})
        visible[node] = names[node]
    return entries


def _name_leaves(node):
    if node.kind == 'name':
        yield node.text
        return
    for child in node.children:
        yield from _name_leaves(child)


def _validate_bindings(bindings, driver_ids, prefix):
    """Refuse a table that would be wrong (design.md D2): an entry naming
    a later entry, or a name colliding with a declared driver id. Cheap --
    proportional to the table's own text, not the document it replaces --
    and a defect caught here is always the framework's, never a project's:
    a correct table can never trip it.

    The ordering rule binds only MINTED names -- those matching
    `<prefix>\\d+`, `prefix` being exactly what `_mint_prefix` chose for
    this document. Any other leaf name an entry's expression carries ($t
    aside) is the project's business, not this table's: a `scad_inline`
    constant, a name from solid2 the framework never declared, anything the
    consumer already resolves or already refuses on its own -- publishing
    it unexamined is what D2 requires ("refusal is for a table that would
    be wrong, never a project's fault"). Only a name that LOOKS like one of
    this table's own references but does not resolve is a genuine defect:
    an entry naming a later entry, or a stray reference to a name this
    table never minted.
    """
    declared = set(driver_ids)
    earlier = set()
    minted = re.compile(r'\A' + re.escape(prefix) + r'\d+\Z')
    for entry in bindings:
        name, expression = entry['name'], entry['expression']
        if name in declared:
            raise BindingTableError(
                f'binding name {name!r} collides with a declared driver id')
        if name in earlier:
            raise BindingTableError(f'binding name {name!r} is minted twice')
        try:
            node = parse(expression)
        except (ExpressionError, RecursionError) as error:
            # A binding's own text is always something this module rendered
            # from an already-parsed node (bind_expressions never binds an
            # expression it could not read), so this can only mean the
            # renderer and the parser disagree -- a framework defect.
            raise BindingTableError(
                f"binding {name!r}'s expression {expression!r} is not in "
                f'the language this table is written in: {error}') from error
        for leaf in _name_leaves(node):
            if leaf == '$t' or leaf in declared or leaf in earlier:
                continue
            if not minted.match(leaf):
                # An ordinary name this table did not mint: the project's
                # business, unexamined (see the docstring above).
                continue
            raise BindingTableError(
                f'binding {name!r} names {leaf!r}, which looks like a '
                f'minted binding reference but is not $t, a declared '
                f'driver id, or an entry earlier in the table')
        earlier.add(name)


def _matches(original, candidate, names):
    """Whether `candidate` -- parsed from a REWRITTEN string, where a name
    may stand for a shared subtree -- represents the same value as
    `original`, from the full un-rewritten tree.

    Stops as soon as a name resolves, so the cost is proportional to what
    was actually published (short once bound), never to how large the
    original subtree was.
    """
    minted = names.get(original)
    if minted is not None and candidate.kind == 'name' and candidate.text == minted:
        return True
    if original.kind != candidate.kind or original.op != candidate.op:
        return False
    if original.kind in _LEAF_KINDS:
        return original.text == candidate.text
    if len(original.children) != len(candidate.children):
        return False
    return all(_matches(oc, cc, names)
               for oc, cc in zip(original.children, candidate.children))


def _verify_reconstruction(rewritten, parsed, bindings, names):
    """Refuse a rewrite that does not reproduce what the producer built
    (design.md D2) -- a framework defect, never reachable from correct
    model input, since the rewrite is built directly from the same nodes
    this checks against. A safety net, not a re-derivation: cost is
    proportional to the published (small) text, not the document that was
    flattened to build it."""
    entry_text = {entry['name']: entry['expression'] for entry in bindings}
    for node, name in names.items():
        candidate = parse(entry_text[name])
        if not _matches(node, candidate, names):
            raise BindingTableError(
                f'binding {name!r} does not reproduce the subexpression '
                f'it was minted for')
    for text, original in zip(rewritten, parsed):
        if original is None:
            continue
        if names.get(original) == text:
            continue
        candidate = parse(text)
        if not _matches(original, candidate, names):
            raise BindingTableError(
                'a rewritten expression does not reproduce what the '
                'producer built once its bindings are resolved')


def _has_named_descendant(node, names, cache):
    cached = cache.get(node)
    if cached is not None:
        return cached
    found = False
    for child in node.children:
        if child in names or _has_named_descendant(child, names, cache):
            found = True
            break
    cache[node] = found
    return found


def bind_expressions(expressions, driver_ids):
    """The document-level entry point (design.md D3-D5).

    `expressions`: every operation's and flexible leaf's expression string
    in the document, in a fixed walk order. `driver_ids`: every qualified
    driver id declared in the same document (so a minted name can never
    collide with one -- D4).

    Returns `(rewritten, bindings, warnings)`:

    - `rewritten`: one string per input, in the same order. An expression
      touching nothing shared is returned byte-identical to the input; an
      unreadable expression is returned unchanged too. Only an expression
      containing a shared subexpression is rewritten.
    - `bindings`: the ordered table (`[]` when nothing in the document is
      shared -- the caller then omits the `bindings` key entirely).
    - `warnings`: one message per expression the parser could not read,
      already truncated for logging; that expression is in `rewritten`
      verbatim and contributes nothing to `bindings`.

    Never raises for text either producer emits. Raises `BindingTableError`
    only when the table this would publish is wrong -- a framework defect
    (see `_validate_bindings`, `_verify_reconstruction`) -- in which case
    nothing is returned and the document must not be written.
    """
    interner = Interner()
    memo = {}
    parsed = []
    warnings = []
    for expression in expressions:
        if not isinstance(expression, str):
            # Defensive, not reachable from any current producer: every
            # operation stringifies (`operations.py`'s `serialized`), and
            # `unserialize()` -- the one path that does not -- has no
            # caller (tasks.md 3.4). Not text at all, so not "unreadable"
            # either: returned untouched, and silently, since there is
            # nothing to warn about.
            parsed.append(None)
            continue
        try:
            node = parse(expression, interner, memo)
        except ExpressionError as error:
            parsed.append(None)
            message = (
                f'an expression could not be read by the bindings pass and '
                f'will be published verbatim and unshared: {error} '
                f'(text: {_truncate(expression)!r})')
            warnings.append(message)
            logger.warning(message)
            continue
        except RecursionError:
            # Exhausted the parser's stack depth -- treated exactly like
            # unreadable text (design.md D2's "verbatim and unshared", not
            # a build failure): a deeply left-nested chain in the shape
            # solid2 itself builds (each level its own parenthesised
            # group) costs the parser several stack frames per level, so a
            # legal document can still exceed Python's default recursion
            # limit long before it exceeds any grammar the parser reads.
            parsed.append(None)
            message = (
                f'an expression is too deeply nested for the bindings pass '
                f'and will be published verbatim and unshared '
                f'(text: {_truncate(expression)!r})')
            warnings.append(message)
            logger.warning(message)
            continue
        parsed.append(node)

    shared_nodes = [node for node in interner.order
                    if _is_bindable(node) and interner.counts.get(node, 0) > 1]

    if not shared_nodes:
        return list(expressions), [], warnings

    prefix = _mint_prefix(driver_ids)
    names = _mint_names(shared_nodes, prefix)
    bindings = _bindings_list(shared_nodes, names)
    _validate_bindings(bindings, driver_ids, prefix)

    cache = {}
    rewritten = []
    for expression, node in zip(expressions, parsed):
        if node is None:
            rewritten.append(expression)
            continue
        minted = names.get(node)
        if minted is not None:
            rewritten.append(minted)
        elif _has_named_descendant(node, names, cache):
            rewritten.append(render(node, names))
        else:
            rewritten.append(expression)

    _verify_reconstruction(rewritten, parsed, bindings, names)
    return rewritten, bindings, warnings
