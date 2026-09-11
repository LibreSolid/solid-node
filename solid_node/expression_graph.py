# Copyright (C) 2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Native immutable motion operations. No modelling backend or global arena.

Values own their reachable operands. Identity hashing is intentional: structural
interning is the document compiler's job, and must never recursively hash a DAG.
"""

from dataclasses import dataclass


@dataclass(frozen=True, eq=False, slots=True, repr=False, weakref_slot=True)
class ExpressionNode:
    kind: str
    op: str = ''
    children: tuple = ()
    text: str = ''

    def __repr__(self):
        detail = self.text if self.kind in ('name', 'num', 'raw') else self.op
        return f'<ExpressionNode {self.kind} {detail[:80]!r}>'


def postorder(roots):
    """Visit each reachable identity once, operands before their consumers."""
    seen = set()
    for root in roots:
        stack = [(root, False)]
        while stack:
            node, ready = stack.pop()
            if node in seen:
                continue
            if ready:
                seen.add(node)
                yield node
            else:
                stack.append((node, True))
                stack.extend((child, False) for child in reversed(node.children))


def free_names(node):
    return {item.text for item in postorder([node]) if item.kind == 'name'}
