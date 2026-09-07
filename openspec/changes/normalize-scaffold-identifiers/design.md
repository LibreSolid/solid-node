## Context

`New.handle()` replaces non-ASCII-alphanumeric/underscore characters with
underscores, strips boundary underscores, and falls back to `project`. It then
uses that value for the target directory, package, module filename, and
manifest, while deriving a Pascal-style class name from underscore-separated
parts. This handles `snowman-3` but admits `3d_printer`, whose generated class
starts with a digit, and Python keywords such as `class`, which are not valid
package identifiers under the stated contract.

The scaffold must choose one final package identifier before checking the
target or writing any file. Every generated reference must derive from that
same value.

## Goals / Non-Goals

**Goals:**

- Produce a valid, non-keyword Python package identifier for every input
  basename.
- Produce a valid class identifier derived from that final package name.
- Keep normalization deterministic and preserve existing outputs where they
  are already valid.
- Ensure the target directory, package directory, modules, tests, and manifest
  agree on the normalized identity.
- Prove generated digit-leading and keyword projects compile, build, and test
  without edits.

**Non-Goals:**

- Preserve a broken scaffold's previous `3d_printer` directory name.
- Accept Unicode letters in generated identifiers; the existing ASCII rule
  remains.
- Add collision resolution when two raw names normalize to the same target.
- Change template content or printed browser/port guidance.

## Decisions

### D1: Prefix unusable sanitized package names with `project_`

After the existing character replacement, boundary stripping, and `project`
fallback, normalization will test `str.isidentifier()` and
`keyword.iskeyword()`. A leading-digit result or keyword will become
`project_<name>`. Thus `3d-printer` becomes `project_3d_printer`, `class`
becomes `project_class`, `snowman-3` remains `snowman_3`, and punctuation-only
input remains `project`.

Rejecting these inputs was considered, but the command already promises
normalization and can produce a clear deterministic identity. Prefixing only
the class was rejected because the package would still violate the stated
identifier contract. A leading underscore was rejected because deriving a
class would then need a separate special rule and the generated names would be
less descriptive.

### D2: Derive every generated name from one helper result

A small helper will return `(package, class_name)`. `New.handle()` will use
that pair for the normalized target path, package/module/test filenames,
template substitutions, and manifest reference. Centralizing this calculation
prevents one output path from retaining the raw or pre-prefix spelling.

Scattering an extra leading-digit conditional beside the class derivation was
rejected because keyword handling and future consumers could diverge again.

### D3: Derive the class after package normalization

The existing underscore-part capitalization will run on the final package.
The `project_` prefix therefore yields `Project3dPrinter` and `ProjectClass`,
both valid and consistent with the manifest. Existing valid cases keep their
current class names.

### D4: Test both generated syntax and the actual scaffold workflow

Focused table tests will pin package/class results for ordinary, punctuated,
digit-leading, keyword, and empty-after-sanitization names. Generated source
and test modules will be compiled. Acceptance coverage will enter numeric and
keyword projects and invoke the real build and test managers, establishing
that import resolution and companion-test discovery agree with the manifest.
The saved public probe will continue to run `solid new 3d-printer` followed by
`solid build`.

## Risks / Trade-offs

- **Users may expect the target to remain `3d_printer`.** → The prior target
  contains unusable generated source; stdout and tests make the deterministic
  `project_3d_printer` result explicit.
- **Two inputs can still normalize to one target.** → Existing overwrite
  refusal protects data; collision disambiguation is outside F08.
- **A later identifier policy might allow Unicode.** → The helper preserves the
  current ASCII contract and is a single place to revise it later.

## Migration Plan

No migration is required. The change affects only newly scaffolded projects.
Rollback restores the former naming bug without changing existing projects.

## Open Questions

None.
