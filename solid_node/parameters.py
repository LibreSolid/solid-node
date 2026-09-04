# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Build parameters: the knobs that decide what machine gets built.

A parameter is what a maker chooses before anything is manufactured --
a bore, a tooth count, whether the enclosure has a lid. It is fixed for
the life of an instance, it decides the machine's build identity, and
structure may depend on it. That is exactly what a driver is not: a
driver is a runtime input, it changes every instant, and structure may
never depend on it. The two live in modules of their own so an import
line says which is which::

    from solid_node.node import AssemblyNode, CadQueryNode
    from solid_node.parameters import Length, Flag
    from solid_node.simulation import Driver

Three ideas, one mechanism each:

- A declared parameter is a symbolic TOKEN. Arithmetic over tokens
  builds a formula whose dimension is computed as it is built, so a
  mismatch (`bore + pressure_angle`) raises in the class body, on
  import, before any geometry exists. The same tree evaluates against an
  instance's bound values at instantiation, producing a plain float. One
  implementation, run once symbolically and once concretely.

- A dimension is a mapping from axis to integer exponent, and the
  algebra is arithmetic on exponents: products add them, quotients
  subtract them, sums require them equal. Derived kinds exist whether or
  not they are named (`Length * Length` is a valid quantity), and a
  project extends the ontology by subclassing `Quantity` with its own
  exponents; the engine never enumerates kinds. Dimensions only, never
  units -- the framework already fixes millimetres and degrees.

- A declaration is a descriptor that names itself when assigned, refuses
  to be shadowed or assigned on an instance, and reads back as a plain
  Python value on an instance and as its token on the class.

This module imports nothing. Not from the framework, not from a third
party, only the standard library's absence of it: it is on the import
path of every node module in every project and holds only declarations
and arithmetic over exponents, so it must cost nothing to reach. Its
names are bound eagerly for the same reason -- there is nothing
expensive to defer.

The two declarations a class body makes that are NOT parameters live in
`solid_node.node.declarative`, which imports this module: the children a
class declares, and the metaclass that makes a class body recognizable.
`solid_node.node.ports` holds the third, and `DriverDeclaration` in
`solid_node.node.qualified` the runtime one; all four follow the same
descriptor discipline defined here by `Declaration`.
"""


__all__ = [
    'Quantity',
    'Length',
    'Angle',
    'Count',
    'Ratio',
    'Scalar',
    'Flag',
    'Expression',
    'Formula',
    'declared_parameters',
    'DimensionError',
    'ParameterError',
]


_MISSING = object()


class DimensionError(TypeError):
    """Two quantities were combined in a way their dimensions forbid."""


class ParameterError(ValueError):
    """A parameter value is missing or violates its declaration."""


##############################################
# Dimensions

def _normalized(dimension):
    """A dimension mapping with zero exponents dropped, so two ways of
    reaching the same dimension compare equal."""
    return {axis: exponent for axis, exponent in sorted(dimension.items())
            if exponent}


def _combined(left, right, sign):
    """left + sign * right, exponent by exponent."""
    result = dict(left)
    for axis, exponent in right.items():
        result[axis] = result.get(axis, 0) + sign * exponent
    return _normalized(result)


def _describe(operand):
    """How an operand reads in an error: its declared name when the
    class body has given it one, its dimension otherwise."""
    name = getattr(operand, '_name', None)
    if name:
        return name
    if isinstance(operand, Expression):
        return f'<{operand.describe_dimension()}>'
    return repr(operand)


def _dimension_of(operand):
    if isinstance(operand, Expression):
        return operand.dimension
    return {}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def evaluate(operand, values):
    # A token or formula resolves against the realizing instance's
    # values; so does a Flag, which is outside the algebra but flows to
    # a child like any other declaration. Anything else passes through.
    if isinstance(operand, (Expression, Flag)):
        return operand.evaluate(values)
    return operand


##############################################
# The descriptor discipline shared by every declaration

# Instance attributes AbstractBaseNode.__init__ assigns. A declaration
# is read as an attribute of its node, so a declaration by one of these
# names would either be assigned over in __init__ or shadow what every
# caller of that attribute expects.
_RESERVED = frozenset({
    'name', 'uniq_id', 'operations', 'checkpoint', 'src', 'basedir',
    'build_dir', 'scad_file', 'stl_file', 'brep_file', 'mesh_scad_file',
    'mesh_stl_file', 'lock_file', 'local_stl', 'basepath', 'files', 'model',
    'root',
})


class Declaration:
    """What a parameter, a derived formula and a flag share: a class
    attribute that names itself when assigned and refuses to be
    shadowed or assigned on an instance.

    A DATA descriptor, deliberately: a `__get__`-only descriptor loses
    to an instance attribute of the same name, so `self.bore = 5` would
    silently replace the declaration for every later read. `__set__`
    raising is what makes that an error instead.
    """

    _name = None
    derived = False

    def __set_name__(self, owner, name):
        if self._name is not None and self._name != name:
            raise TypeError(
                f"'{name}' on {owner.__name__} is the declaration already "
                f"named '{self._name}': a declaration is one parameter, so "
                f"it cannot be assigned under two names. Declare a second "
                f"parameter, or derive one from the other.")
        if name in _RESERVED:
            raise TypeError(
                f"parameter '{name}' on {owner.__name__} would shadow the "
                f"node attribute '{name}', which every node carries. Rename "
                f"the parameter.")
        for klass in owner.__mro__[1:]:
            # A sentinel, not None: `color = None` on the base is an
            # attribute every caller reads, and a declaration by that
            # name would shadow it just the same.
            existing = vars(klass).get(name, _MISSING)
            if existing is _MISSING or isinstance(existing, Declaration):
                continue
            raise TypeError(
                f"parameter '{name}' on {owner.__name__} would shadow "
                f"{klass.__name__}.{name}, which a parameter read would then "
                f"hide for good. A parameter is read as an attribute of its "
                f"node, so its name has to be free on that node: rename the "
                f"parameter.")
        self._name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        try:
            return instance.__dict__['_parameters'][self._name]
        except KeyError:
            raise AttributeError(
                f"parameter '{self._name}' of {type(instance).__name__} is "
                f"not resolved on this instance") from None

    def __set__(self, instance, value):
        raise AttributeError(
            f"parameter '{self._name}' of {type(instance).__name__} cannot "
            f"be assigned: a declared parameter is resolved when the node is "
            f"constructed, and a derived one follows its inputs. Pass "
            f"{self._name}={value!r} to the constructor instead.")

    def __bool__(self):
        raise TypeError(
            f"'{self._name or type(self).__name__}' is a declaration, not a "
            f"value: a condition on it belongs in render(), where "
            f"self.{self._name or '<name>'} is the resolved value.")


##############################################
# Expressions: tokens and formulas

class Expression:
    """Anything with a dimension that arithmetic can combine.

    `dimension` is a mapping from axis to exponent, `{}` for
    dimensionless, and `None` for unchecked (the `Scalar` escape hatch,
    which any operation involving one propagates). `evaluate(values)`
    computes the concrete value against a mapping of resolved parameter
    values.
    """

    dimension = {}

    @property
    def unchecked(self):
        return self.dimension is None

    def describe_dimension(self):
        if self.dimension is None:
            return 'unchecked'
        if not self.dimension:
            return 'dimensionless'
        return ' '.join(f'{axis}^{exponent}' if exponent != 1 else axis
                        for axis, exponent in self.dimension.items())

    def evaluate(self, values):
        raise NotImplementedError

    @property
    def value(self):
        """The same expression with its dimension unchecked, so the
        ontology never makes something inexpressible."""
        return Formula(lambda x: x, (self,), None, symbol='value')

    # -- the algebra ----------------------------------------------------

    def _operand(self, other, symbol):
        if isinstance(other, Expression) or _is_number(other):
            return other
        raise TypeError(
            f"unsupported operand for {symbol}: {_describe(self)} and "
            f"{other!r}. Only declared quantities and plain numbers take "
            f"part in a parameter formula.")

    def _additive(self, other, symbol, function, reverse=False):
        other = self._operand(other, symbol)
        left, right = (other, self) if reverse else (self, other)
        if self.dimension is None or _dimension_of(other) is None:
            dimension = None
        else:
            mine, theirs = _normalized(self.dimension), \
                _normalized(_dimension_of(other))
            if mine != theirs:
                raise DimensionError(
                    f"cannot compute {_describe(left)} {symbol} "
                    f"{_describe(right)}: {_describe(left)} is "
                    f"{_expression_dimension(left)} and {_describe(right)} is "
                    f"{_expression_dimension(right)}. Addition and "
                    f"subtraction need equal dimensions.")
            dimension = mine
        return Formula(function, (left, right), dimension, symbol=symbol)

    def __add__(self, other):
        return self._additive(other, '+', lambda a, b: a + b)

    def __radd__(self, other):
        return self._additive(other, '+', lambda a, b: a + b, reverse=True)

    def __sub__(self, other):
        return self._additive(other, '-', lambda a, b: a - b)

    def __rsub__(self, other):
        return self._additive(other, '-', lambda a, b: a - b, reverse=True)

    def _multiplicative(self, other, symbol, function, sign, reverse=False):
        other = self._operand(other, symbol)
        left, right = (other, self) if reverse else (self, other)
        if self.dimension is None or _dimension_of(other) is None:
            dimension = None
        else:
            dimension = _combined(_dimension_of(left), _dimension_of(right),
                                  sign)
        return Formula(function, (left, right), dimension, symbol=symbol)

    def __mul__(self, other):
        return self._multiplicative(other, '*', lambda a, b: a * b, 1)

    def __rmul__(self, other):
        return self._multiplicative(other, '*', lambda a, b: a * b, 1,
                                    reverse=True)

    def __truediv__(self, other):
        return self._multiplicative(other, '/', lambda a, b: a / b, -1)

    def __rtruediv__(self, other):
        # other / self: exponents of `other` minus those of `self`.
        other = self._operand(other, '/')
        if self.dimension is None or _dimension_of(other) is None:
            dimension = None
        else:
            dimension = _combined(_dimension_of(other), self.dimension, -1)
        return Formula(lambda a, b: a / b, (other, self), dimension,
                       symbol='/')

    def __pow__(self, exponent):
        if not isinstance(exponent, int) or isinstance(exponent, bool):
            raise TypeError(
                f"{_describe(self)} ** {exponent!r}: a parameter formula "
                f"takes only an integer power; use sqrt() from "
                f"solid_node.math for a root.")
        if self.dimension is None:
            dimension = None
        else:
            dimension = _normalized({
                axis: value * exponent
                for axis, value in self.dimension.items()})
        return Formula(lambda a, b: a ** b, (self, exponent), dimension,
                       symbol='**')

    def __neg__(self):
        return Formula(lambda a: -a, (self,), self.dimension, symbol='-')

    def __pos__(self):
        return self

    def _compare(self, other):
        raise TypeError(
            f"cannot compare {_describe(self)} in a declaration: a "
            f"comparison belongs in render(), on the resolved values.")

    __lt__ = __le__ = __gt__ = __ge__ = _compare


def _expression_dimension(operand):
    if isinstance(operand, Expression):
        return operand.describe_dimension()
    return 'dimensionless'


class Formula(Expression, Declaration):
    """A node of the expression tree: a function over operands, with
    the dimension the algebra assigned when it was built.

    Also a declaration: a formula assigned in a class body is a derived
    parameter, read on the instance as the evaluated value, refused on
    assignment, and enumerable beside the declared ones.
    """

    derived = True

    def __init__(self, function, operands, dimension, symbol=None):
        self._function = function
        self._operands = tuple(operands)
        self.dimension = dimension
        self._symbol = symbol

    def evaluate(self, values):
        return self._function(*[evaluate(operand, values)
                                for operand in self._operands])

    def __repr__(self):
        if self._name:
            return f'<derived {self._name}: {self.describe_dimension()}>'
        return f'<formula {self._symbol}: {self.describe_dimension()}>'


def function_formula(name, numeric, *args):
    """A formula applying one of `solid_node.math`'s functions to
    declared quantities, with that function's dimension rule.

    `sqrt` needs even exponents and halves them; the trig functions
    need an angle and return dimensionless; the inverse trig functions
    need dimensionless arguments and return an angle. `numeric` is the
    function's own numeric mode, so evaluation and the class body agree
    on degrees.
    """
    dimensions = [_dimension_of(arg) for arg in args]
    if any(dimension is None for dimension in dimensions):
        return Formula(numeric, args, None, symbol=name)
    normalized = [_normalized(dimension) for dimension in dimensions]
    if name == 'sqrt':
        (dimension,) = normalized
        if any(exponent % 2 for exponent in dimension.values()):
            raise DimensionError(
                f"sqrt({_describe(args[0])}): {_describe(args[0])} is "
                f"{_expression_dimension(args[0])}, and a square root needs "
                f"even exponents.")
        result = _normalized({axis: exponent // 2
                              for axis, exponent in dimension.items()})
    elif name in ('sin', 'cos', 'tan'):
        (dimension,) = normalized
        if dimension != {'A': 1}:
            raise DimensionError(
                f"{name}({_describe(args[0])}): {_describe(args[0])} is "
                f"{_expression_dimension(args[0])}, and {name} takes an "
                f"Angle.")
        result = {}
    elif name in ('asin', 'acos', 'atan'):
        (dimension,) = normalized
        if dimension:
            raise DimensionError(
                f"{name}({_describe(args[0])}): {_describe(args[0])} is "
                f"{_expression_dimension(args[0])}, and {name} takes a "
                f"dimensionless quantity.")
        result = {'A': 1}
    elif name == 'atan2':
        if normalized[0] != normalized[1]:
            raise DimensionError(
                f"atan2({_describe(args[0])}, {_describe(args[1])}): the two "
                f"arguments are {_expression_dimension(args[0])} and "
                f"{_expression_dimension(args[1])}, and atan2 needs them "
                f"equal.")
        result = {'A': 1}
    else:
        raise ValueError(f'unknown function {name!r}')
    return Formula(numeric, args, result, symbol=name)


##############################################
# The kinds

class Quantity(Expression, Declaration):
    """A declared parameter of one dimension: a token in formulas, a
    descriptor on the class, a plain value on the instance.

    Subclass with a `dimension` mapping to declare a kind the framework
    does not name (`class Torque(Quantity): dimension = {'M': 1, 'L': 2,
    'T': -2}`); the algebra needs nothing else.
    """

    dimension = {}
    coerce = float

    def __init__(self, default=_MISSING, *, min=None, max=None):
        self.default = default
        self.min = min
        self.max = max

    @property
    def required(self):
        return self.default is _MISSING

    def evaluate(self, values):
        if self._name is None:
            # A token that never reached a class body (an inline
            # `Length(2.0)` in a child declaration): a constant.
            return self.resolve(self.default, '<inline>')
        try:
            return values[self._name]
        except KeyError:
            raise ParameterError(
                f"'{self._name}' is not declared on the class evaluating "
                f"this formula; a formula may only use this class's own "
                f"parameters") from None

    def resolve(self, value, owner):
        """The concrete value of this declaration for one instance:
        coerced to the kind and checked against the constraints."""
        if value is _MISSING:
            raise ParameterError(
                f"{owner} needs a value for '{self._name}': it declares no "
                f"default, so the parent's declaration or the caller "
                f"(Python or --set on the command line) must supply it.")
        try:
            resolved = self.coerce(value)
        except (TypeError, ValueError) as failure:
            raise ParameterError(
                f"{owner}: '{self._name}' cannot take {value!r}: "
                f"{failure}") from None
        if self.min is not None and resolved < self.min:
            raise ParameterError(
                f"{owner}: '{self._name}' must be at least {self.min}, "
                f"got {resolved!r}")
        if self.max is not None and resolved > self.max:
            raise ParameterError(
                f"{owner}: '{self._name}' must be at most {self.max}, "
                f"got {resolved!r}")
        return resolved

    def parse(self, text):
        """The value one `--set` word means for this kind."""
        try:
            return self.coerce(text)
        except (TypeError, ValueError) as failure:
            raise ParameterError(
                f"'{self._name}' cannot take {text!r}: {failure}") from None

    def __repr__(self):
        return (f'<{type(self).__name__} {self._name or "?"} = '
                f'{"required" if self.required else self.default!r}>')


def _float(value):
    if isinstance(value, bool):
        raise TypeError('a boolean is not a number')
    return float(value)


def _int(value):
    if isinstance(value, bool):
        raise TypeError('a boolean is not a count')
    if isinstance(value, str):
        return int(value)
    if isinstance(value, float) and not value.is_integer():
        raise TypeError(f'{value!r} is not a whole number')
    return int(value)


class Length(Quantity):
    """A linear dimension, in the project's unit (millimetres). Signed
    by default; `min=0` opts into non-negativity."""

    dimension = {'L': 1}
    coerce = staticmethod(_float)


class Angle(Quantity):
    """An angle in degrees. Its own axis: formally dimensionless, but
    keeping it apart is what refuses `phase + rotor_fraction` and lets
    trig demand an angle."""

    dimension = {'A': 1}
    coerce = staticmethod(_float)


class Count(Quantity):
    """A whole number of things: teeth, cylinders, sides."""

    dimension = {}
    coerce = staticmethod(_int)


class Ratio(Quantity):
    """A dimensionless fraction; also what a Length over a Length is."""

    dimension = {}
    coerce = staticmethod(_float)


class Scalar(Quantity):
    """The escape hatch: a number the algebra does not check."""

    dimension = None
    coerce = staticmethod(_float)


def _bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    raise TypeError(f'{value!r} is not a boolean (expected true or false)')


class Flag(Declaration):
    """A boolean selector, outside the algebra: it gates structure
    through omit(), never enters a formula."""

    def __init__(self, default=_MISSING):
        self.default = default

    coerce = staticmethod(_bool)

    @property
    def required(self):
        return self.default is _MISSING

    def resolve(self, value, owner):
        if value is _MISSING:
            raise ParameterError(
                f"{owner} needs a value for '{self._name}': it declares no "
                f"default, so the parent's declaration or the caller "
                f"(Python or --set on the command line) must supply it.")
        try:
            return self.coerce(value)
        except TypeError as failure:
            raise ParameterError(
                f"{owner}: '{self._name}' cannot take {value!r}: "
                f"{failure}") from None

    def evaluate(self, values):
        """The parent's resolved boolean, when this flag is passed to a
        declared child; an inline `Flag(True)` is a constant."""
        if self._name is None:
            return self.resolve(self.default, '<inline>')
        try:
            return values[self._name]
        except KeyError:
            raise ParameterError(
                f"'{self._name}' is not declared on the class realizing "
                f"this child; a flag passed to a child may only be this "
                f"class's own") from None

    parse = Quantity.parse

    def __repr__(self):
        return (f'<Flag {self._name or "?"} = '
                f'{"required" if self.required else self.default!r}>')


##############################################
# Enumeration

_parameters_cache = {}


def declared_parameters(node_class):
    """Every parameter declared on `node_class`, by name, declared and
    derived alike, base-first so a subclass redeclaration wins.

    The structural counterpart lives next door: `declared_children` in
    `solid_node.node.declarative` answers the same question about the
    children a class body declares.
    """
    cached = _parameters_cache.get(node_class)
    if cached is None:
        found = {}
        for klass in reversed(node_class.__mro__):
            for name, value in vars(klass).items():
                if isinstance(value, Declaration):
                    found[name] = value
        cached = _parameters_cache[node_class] = found
    return cached
