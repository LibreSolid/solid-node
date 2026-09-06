# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""`solid import-step`: scaffold declarative source from a STEP document.

One-shot, project-owned, never a node: this module reads a document's
assembly structure through `solid_node.node.adapters.step.StepAssembly`
and writes `parts.py` (one `StepNode` subclass per part) and
`assembly.py` (one `AssemblyNode` subclass per assembly product, placed
at rest), in the declarative class-body idiom of `docs/declaring.rst`.
Neither generated file is ever overwritten, and nothing here loads a
node or touches `pyproject.toml` -- the manifest lines are printed for
the pilot to add (design D6, D9, D10 of step-assembly-import).

The exact-geometry kernel is imported lazily, inside `handle()`, so
`solid -h` costs nothing here and a broken or absent installation is a
checked failure naming the remedy, not a traceback (design D6's risk
note, CLI spec "the kernel is missing").
"""

import os
import re
import sys


#: A run of characters that is neither an ASCII letter nor an ASCII
#: digit splits a product name into pieces (spec "Generated part
#: source" / "Generated assembly source"): the one splitting rule both
#: the class-name and the attribute-name rules are built from.
_PIECE_RE = re.compile(r'[A-Za-z0-9]+')

#: A rotation or a translation component this close to zero is the
#: identity and is never emitted (design D8) -- the same order of
#: magnitude as the reader's own propriety and zero-angle tolerances.
_ZERO_TOLERANCE = 1e-9


def _pieces(name):
    return _PIECE_RE.findall(name or '')


def _class_name_base(name):
    """The class-name rule (spec D7): split on non-alphanumeric runs,
    upper-case only the first character of each piece when it is a
    letter, concatenate -- inserting an underscore only where a piece
    ending in a digit would otherwise run into a piece starting with a
    digit -- and prefix `Part` when the result would not start with a
    letter.

        '10010 Stator'      -> 'Part10010Stator'
        '40x50x6mm_Bearing' -> 'Part40x50x6mmBearing'
        'M4_12mm_Screw'     -> 'M4_12mmScrew'
        'ODrive_S1'         -> 'ODriveS1'
    """
    pieces = _pieces(name)
    if not pieces:
        return 'Unnamed'
    parts = []
    for piece in pieces:
        if piece[0].isalpha():
            piece = piece[0].upper() + piece[1:]
        if parts and parts[-1][-1].isdigit() and piece[0].isdigit():
            parts.append('_')
        parts.append(piece)
    result = ''.join(parts)
    if not result[0].isalpha():
        result = 'Part' + result
    return result


def _attribute_name_base(name):
    """The attribute-name rule (spec "Generated assembly source"): the
    same pieces, lower-cased and joined with underscores, prefixed
    `p_` when the result would not start with a letter."""
    pieces = [piece.lower() for piece in _pieces(name)]
    if not pieces:
        return 'unnamed'
    result = '_'.join(pieces)
    if not result[0].isalpha():
        result = 'p_' + result
    return result


def _unique(base, seen):
    """`base`, or `base_2`, `base_3`, ... the second and later time it
    is asked for -- the collision suffix design D7 and the assembly
    spec both name, in document order."""
    count = seen.get(base, 0) + 1
    seen[base] = count
    return base if count == 1 else f'{base}_{count}'


def _literal(value):
    """A clean float literal for generated source: zero is never
    `-0.0` (rounding a near-zero negative like -3e-17 produces one even
    though the pre-rounded value already compares equal to zero), and
    nine decimal places is nanometre precision -- far inside the
    0.01 mm faithfulness the spec asks of the generated model, and far
    cleaner to read than a raw float repr."""
    rounded = round(value, 9)
    if rounded == 0:
        rounded = 0.0
    return repr(rounded)


def _is_identity_angle(angle_deg):
    return abs(angle_deg) <= _ZERO_TOLERANCE


def _is_identity_translation(translation):
    return all(abs(component) <= _ZERO_TOLERANCE for component in translation)


##############################################
# parts.py


def _part_class_source(class_name, step_source, part_name):
    return (
        f"class {class_name}(StepNode):\n\n"
        f"    step_source = {step_source!r}\n"
        f"    part = {part_name!r}\n\n"
        f"    # A vendor document is fillets and threads; the framework's\n"
        f"    # 0.1 rad default costs an order of magnitude in artifact\n"
        f"    # size (19.91 MB against 1.76 MB measured on one part).\n"
        f"    angular_deflection = 0.5\n")


def generate_parts(assembly, step_file, into_dir):
    """`(source_text, {product_name: class_name})` for `parts.py`: one
    `StepNode` subclass per product that is a part (spec "Generated
    part source"), never for a sub-assembly or the root."""
    step_relative = os.path.relpath(os.path.realpath(step_file),
                                    os.path.realpath(into_dir))

    seen = {}
    class_names = {}
    bodies = []
    for product in assembly.products:
        if product.kind != 'part':
            continue
        class_name = _unique(_class_name_base(product.name), seen)
        class_names[product.name] = class_name
        bodies.append(_part_class_source(class_name, step_relative,
                                         product.name))

    header = (
        f"# Solid Node - generated by `solid import-step`\n\n"
        f'"""Parts scaffolded from {os.path.basename(step_file)!r} by '
        f'`solid import-step`.\n\n'
        f"Generated once; edit freely -- running the command again\n"
        f"refuses to overwrite this file (see docs/cli.rst).\n"
        f'"""\n\n'
        f"from solid_node.node import StepNode\n\n\n")
    source = header + '\n\n'.join(bodies) + ('\n' if bodies else '')
    return source, class_names


##############################################
# assembly.py


def _ordered_assembly_names(assembly):
    """Every class `assembly.py` must declare, children before parents
    (design D6's generator note: a class body may only reference a
    name Python has already defined) -- `None`, standing for the
    document's own root, is always last, whether OCCT calls the root
    product a `part` or an assembly: the generated model always has
    one outermost class."""
    assembly_names = {product.name for product in assembly.products
                      if product.kind in ('sub-assembly', 'root assembly')}
    children_by_parent = {}
    for occurrence in assembly.occurrences:
        if occurrence.product_name in assembly_names:
            children_by_parent.setdefault(
                occurrence.parent_name, []).append(occurrence.product_name)

    order = []
    visited = set()

    def visit(name):
        if name in visited:
            return
        visited.add(name)
        for child in children_by_parent.get(name, []):
            visit(child)
        order.append(name)

    visit(None)
    return order


def _attribute_names(occurrences):
    """One attribute name per occurrence of one assembly's direct
    children, in document order: the base name suffixed `_1`, `_2` ...
    only when that assembly places the product more than once (spec
    "Generated assembly source"), and defensively de-duplicated
    against an unrelated product that happens to slug to the same
    base."""
    counts = {}
    for occurrence in occurrences:
        counts[occurrence.product_name] = counts.get(
            occurrence.product_name, 0) + 1

    index = {}
    used = set()
    names = []
    for occurrence in occurrences:
        base = _attribute_name_base(occurrence.product_name)
        if counts[occurrence.product_name] > 1:
            index[occurrence.product_name] = index.get(
                occurrence.product_name, 0) + 1
            candidate = f'{base}_{index[occurrence.product_name]}'
        else:
            candidate = base
        final = candidate
        bump = 1
        while final in used:
            bump += 1
            final = f'{candidate}_{bump}'
        used.add(final)
        names.append(final)
    return names


def _child_expression(occurrence, class_names, assembly_class_names):
    if occurrence.product_name in class_names:
        return f'{class_names[occurrence.product_name]}()'
    return f'{assembly_class_names[occurrence.product_name]}()'


def _placement_lines(attribute, occurrence, step_basename):
    display = occurrence.label_name or occurrence.product_name
    lines = [f'        # {display} ({step_basename})']
    emitted = False
    if not _is_identity_angle(occurrence.angle_deg):
        axis = tuple(_literal(component) for component in occurrence.axis)
        lines.append(
            f'        self.{attribute}.rotate({_literal(occurrence.angle_deg)}, '
            f'({axis[0]}, {axis[1]}, {axis[2]}))')
        emitted = True
    if not _is_identity_translation(occurrence.translation):
        vector = tuple(_literal(component)
                       for component in occurrence.translation)
        lines.append(
            f'        self.{attribute}.translate(({vector[0]}, {vector[1]}, '
            f'{vector[2]}))')
        emitted = True
    if not emitted:
        lines.append(f'        # {attribute} is placed at the identity')
    return lines


def _assembly_class_source(class_name, occurrences, attributes, class_names,
                           assembly_class_names, step_basename):
    lines = [f'class {class_name}(AssemblyNode):', '']
    for attribute, occurrence in zip(attributes, occurrences):
        expression = _child_expression(occurrence, class_names,
                                       assembly_class_names)
        lines.append(f'    {attribute} = {expression}')
    lines.append('')
    lines.append('    def render(self):')
    render_lines = []
    for attribute, occurrence in zip(attributes, occurrences):
        render_lines.extend(
            _placement_lines(attribute, occurrence, step_basename))
    lines.extend(render_lines if render_lines else ['        pass'])
    return '\n'.join(lines) + '\n'


def generate_assembly(assembly, model_name, step_file, class_names):
    """`(source_text, root_class_name)` for `assembly.py`: one
    `AssemblyNode` subclass per assembly product, the root's class
    named from `model_name` (spec "Generated assembly source"). The
    machine is placed at rest: no driver, no `simulate()` (design
    Non-Goals)."""
    step_basename = os.path.basename(step_file)
    order = _ordered_assembly_names(assembly)  # always ends with None

    occurrences_by_parent = {}
    for occurrence in assembly.occurrences:
        occurrences_by_parent.setdefault(
            occurrence.parent_name, []).append(occurrence)

    assembly_class_names = {}
    seen = {}
    for name in order:
        if name is None:
            assembly_class_names[None] = _class_name_base(model_name)
        else:
            assembly_class_names[name] = _unique(_class_name_base(name), seen)
    root_class_name = assembly_class_names[None]

    bodies = []
    for name in order:
        occurrences = occurrences_by_parent.get(name, [])
        attributes = _attribute_names(occurrences)
        bodies.append(_assembly_class_source(
            assembly_class_names[name], occurrences, attributes,
            class_names, assembly_class_names, step_basename))

    part_imports = ', '.join(sorted(set(class_names.values())))
    header = (
        f"# Solid Node - generated by `solid import-step`\n\n"
        f'"""Assembly scaffolded from {step_basename!r} by '
        f'`solid import-step`.\n\n'
        f"Generated once; edit freely -- running the command again\n"
        f"refuses to overwrite this file (see docs/cli.rst). This is\n"
        f"the machine at rest: no driver, no simulate() -- add motion\n"
        f"once the layout looks right.\n"
        f'"""\n\n'
        f"from solid_node.node import AssemblyNode\n\n"
        + (f"from .parts import {part_imports}\n\n\n" if part_imports
           else "\n\n"))
    source = header + '\n\n'.join(bodies)
    return source, root_class_name


def _load_step_assembly():
    """The one seam a test patches to simulate a missing exact-geometry
    kernel (CLI spec "the kernel is missing"; task 6.5)."""
    from solid_node.node.adapters.step import StepAssembly
    return StepAssembly


def _default_model_name(assembly, file_path):
    if assembly.root is not None and assembly.root.name:
        base = assembly.root.name
    else:
        base = os.path.splitext(os.path.basename(file_path))[0]
    slug = re.sub(r'[^A-Za-z0-9]+', '_', base).strip('_').lower()
    return slug or 'model'


def _module_reference(into, module_name, class_name):
    relative = os.path.normpath(os.path.relpath(into, os.getcwd()))
    prefix = '' if relative == os.curdir else relative.replace(os.sep, '.') + '.'
    return f'{prefix}{module_name}:{class_name}'


class ImportStep:
    """Scaffold declarative source from a STEP document's assembly structure."""

    needs_node = False

    def add_arguments(self, parser):
        parser.add_argument(
            'file', metavar='FILE',
            help='The STEP document to read')
        parser.add_argument(
            '--into', default='.', metavar='PACKAGE_DIR',
            help='Package directory to write parts.py and assembly.py '
                 'into (default: the current directory)')
        parser.add_argument(
            '--model', default=None, metavar='NAME',
            help='Name for the generated model (default: derived from '
                 "the document's root product, or the file's stem)")

    def handle(self, args):
        try:
            StepAssembly = _load_step_assembly()
        except ImportError as error:
            sys.stderr.write(
                'Error: import-step needs the exact-geometry kernel '
                '(cadquery, the OCP binding) to read a STEP document; '
                f"install it with 'pip install cadquery'. ({error})\n")
            sys.exit(1)
            return

        try:
            assembly = StepAssembly(args.file)
        except (OSError, ValueError) as error:
            sys.stderr.write(f'Error: {error}\n')
            sys.exit(1)
            return

        improper = [o for o in assembly.occurrences if not o.proper]
        if improper:
            sys.stderr.write(
                'Error: import-step cannot state every placement as a '
                "rotate/translate pair -- the framework's operations "
                'cannot express a mirror or a scale:\n')
            for occurrence in improper:
                display = occurrence.label_name or occurrence.product_name
                sys.stderr.write(
                    f'  {display} (in '
                    f'{occurrence.parent_name or "the document root"}): '
                    f'determinant {occurrence.determinant:.6f}, '
                    f'scale factor {occurrence.scale_factor:.6f}\n')
            sys.stderr.write('Nothing was written.\n')
            sys.exit(1)
            return

        into = args.into
        parts_path = os.path.join(into, 'parts.py')
        assembly_path = os.path.join(into, 'assembly.py')
        for path in (parts_path, assembly_path):
            if os.path.exists(path):
                sys.stderr.write(
                    f'Error: {path} already exists; import-step never '
                    'overwrites generated source. Remove it, or choose '
                    'a different --into, and run the command again.\n')
                sys.exit(1)
                return

        model_name = args.model or _default_model_name(assembly, args.file)

        os.makedirs(into, exist_ok=True)
        init_path = os.path.join(into, '__init__.py')
        if not os.path.exists(init_path):
            open(init_path, 'w').close()

        parts_source, class_names = generate_parts(assembly, args.file, into)
        assembly_source, root_class_name = generate_assembly(
            assembly, model_name, args.file, class_names)

        with open(parts_path, 'w') as handle:
            handle.write(parts_source)
        with open(assembly_path, 'w') as handle:
            handle.write(assembly_source)

        reference = _module_reference(into, 'assembly', root_class_name)

        print(f'Wrote {parts_path}')
        print(f'Wrote {assembly_path}')
        print()
        print('Add to pyproject.toml:')
        print()
        print('[tool.solid-node.models]')
        print(f'{model_name} = "{reference}"')
        print()
        print('Next steps:')
        print(f'  solid build {model_name}')
        print(f'  solid develop {model_name}')
