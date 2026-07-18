# ADR-005: Path-Based Dynamic Module Loading

**Status:** Accepted
**Date:** Unknown
**Depends on:** [ADR-001: Composite Pattern for Node Tree Architecture](../NODE/ADR-001-composite-pattern-node-tree-architecture.md)
**Related to:** [ADR-007: Watchdog Library for Filesystem Monitoring](./ADR-007-watchdog-library-filesystem-monitoring.md)
**Extended by:** [ADR-026: Node Identity — Parameter-Hashed Artifact Keys vs. Tree-Addressing Names](../NODE/ADR-026-node-identity-parameter-hashed-artifact-keys-vs-tree-names.md)

## Context and Problem Statement

The solid-node framework required a mechanism for users to invoke the CLI with references to their node definitions. The fundamental question was: Should users reference nodes via filesystem paths (`solid my_project/root.py develop`) or via Python package names (`solid myproject.root develop`)?

The framework targets mechanical engineers and CAD designers who may not be familiar with Python packaging conventions. The CLI needed to provide an intuitive interface that works without requiring users to understand module imports, `__init__.py` files, or package structure. At the same time, the solution had to support Python's import system for relative imports within user projects.

The loader system converts user-provided file paths into dynamically loaded Python modules at runtime, performing path normalization, module name transformation, and class introspection to find the target node definition.

## Decision Drivers

- User experience prioritizes file-based workflows familiar to engineers (files are tangible, package names are abstract)
- CLI simplicity critical for framework adoption by non-Python-experts
- Must support relative imports in user code without requiring package installation
- Framework should work immediately without project setup or configuration files
- Integration with file watching requires precise source file path tracking
- Node composition depends on tracking which source files contribute to each node's geometry

## Considered Options

1. Path-based loading with dynamic import (chosen)
2. Package-based loading requiring installed modules
3. Configuration file specifying entry points

## Decision Outcome

Chosen option: "Path-based loading with dynamic import", because it provides the most intuitive user experience for the target audience while supporting Python's import system through `sys.path` manipulation.

The implementation performs four key transformations:
1. Resolve absolute path via `os.path.realpath()` (handles symlinks and relative paths)
2. Convert to relative path via `os.path.relpath()` (for module name generation)
3. Transform path separators to dots and strip `.py` extension (`replace('/', '.')[:-3]`)
4. Dynamically import resulting module name and introspect for target class

The loader adds `os.getcwd()` to `sys.path`, enabling relative imports in user code without package installation. Class discovery uses `inspect.getfile(klass) == path` to ensure the target class is defined in the specified file, not imported from elsewhere.

## Pros and Cons of the Options

### Path-based loading with dynamic import

- Good: Intuitive CLI pattern matching file-based workflows (`solid path/to/node.py develop`)
- Good: No package installation or setup required, works immediately
- Good: Supports relative imports through `sys.path` manipulation
- Good: Integrates naturally with file watching (watchdog monitors file paths)
- Bad: `sys.path` modification can cause import shadowing if user projects have names matching installed packages
- Bad: Import behavior depends on working directory, potentially non-reproducible
- Bad: Implicit single-class-per-file assumption (loader returns first match)
- Bad: Less Pythonic than standard package-based imports

### Package-based loading requiring installed modules

- Good: Standard Python approach, familiar to experienced developers
- Good: No `sys.path` manipulation required
- Good: Reproducible import behavior independent of working directory
- Bad: Requires users to understand Python packaging (`setup.py`, `__init__.py`, installation)
- Bad: Higher barrier to entry for non-Python-expert engineers
- Bad: Still requires path information for file watching integration
- Bad: Complicates quick prototyping and experimentation workflow

### Configuration file specifying entry points

- Good: Explicit declaration of project structure and entry points
- Good: Could support additional metadata (project name, version, dependencies)
- Bad: Adds configuration overhead for simple single-node projects
- Bad: Users must learn configuration file format and semantics
- Bad: File-based workflows less direct (edit config to change entry point)

## Consequences

The path-based approach defines the framework's public interface and user experience. All CLI invocations use the `solid <path>` pattern, making file paths a fundamental part of the framework's API contract. Changing to package-based loading would break all existing user projects.

The `sys.path.append(os.getcwd())` line enables relative imports but introduces potential import shadowing. Users should work from their project root directory consistently to avoid import resolution issues. Projects with folder names matching installed packages (e.g., a folder named `requests/`) may experience unexpected import behavior.

The single-class-per-file assumption is implicit. If users define multiple `AbstractBaseNode` subclasses in one file, the loader returns the first match based on `module.__dict__` iteration order. This could cause subtle bugs. The framework does not validate or warn about multiple classes.

Test file discovery follows convention-based patterns: `root.py` maps to `test_root.py`, and `root/__init__.py` maps to `root/test.py`. This mirrors pytest conventions while giving users flexibility to organize tests alongside code or in separate files.

The refactor system integration injects `RefactorRequest` subclasses into user module namespaces via `setup_module()`, allowing user code to raise framework exceptions without explicit imports. This convenience increases implicit coupling between loader and refactor system.

Path resolution via `os.path.realpath()` followed by `os.path.relpath()` ensures consistent module naming regardless of how paths are specified on CLI (relative, absolute, or symlinked). This robustness is essential for CLI tools invoked from various directories.

## References

- `solid_node/core/loader.py:25` - `sys.path` modification
- `solid_node/core/loader.py:27-56` - Path-to-module conversion and class discovery
- `solid_node/core/loader.py:68-72` - Node and test loading entry points
- `solid_node/cli.py` - CLI path argument handling
- `solid_node/manager/develop.py` - Develop manager using `load_node()`
