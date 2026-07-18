# ADR-021: Snapshot CLI Command for AI Agent Autonomy

**Status:** Accepted
**Date:** 2026-01-10 (status corrected 2026-07-18: the command shipped as `solid snapshot <path>` — implemented in `solid_node/manager/snapshot.py`, grammar per [ADR-024](./ADR-024-command-first-cli-grammar-and-duck-typed-command-registry.md), exercised by [ADR-019]'s successor agents; this record had been left at Proposed)
**Depends on:** [ADR-004: Multi-CAD Backend Adapter Pattern](../NODE/ADR-004-multi-cad-backend-adapter-pattern.md)
**Related to:** [ADR-008: Time-Based Animation System for Assemblies](../NODE/ADR-008-time-based-animation-system-for-assemblies.md)

## Context and Problem Statement

AI agents are increasingly being used to develop CAD projects with solid-node. These agents can write code, run tests, and iterate on designs. However, they currently lack the ability to "see" the visual results of their work. The existing `develop` command launches interactive viewers (web or OpenSCAD GUI) designed for human interaction, which agents cannot meaningfully use.

This creates a fundamental gap in the autonomous development workflow: agents can verify mechanical properties through the test framework (collision detection, distance checks, containment), but cannot verify visual/aesthetic properties or debug visual issues without human intervention.

The goal is to enable AI agents to complete the full feedback loop for autonomous CAD development by providing a CLI command that renders nodes to image files.

## Decision Drivers

- **Agent autonomy**: AI agents need visual feedback to iterate on designs without human intervention
- **CLI-first design**: The solution must work entirely through the command line, compatible with agent tooling
- **Animation support**: Must handle AssemblyNode time-based animations (render at specific time values)
- **Minimal dependencies**: Leverage existing OpenSCAD installation rather than adding new rendering dependencies
- **Consistency with architecture**: Follow established patterns from ADR-004 (OpenSCAD as universal compilation target)
- **Flexible camera control**: Agents need to view models from arbitrary angles for comprehensive inspection
- **Integration with existing workflow**: Fit naturally alongside `develop` and `test` commands

## Considered Options

1. **OpenSCAD CLI-based snapshot command** (Chosen)
2. **Headless browser capture of web viewer**
3. **Custom OpenGL/Three.js headless renderer**
4. **CadQuery/OCP-based rendering**

## Decision Outcome

Chosen option: **OpenSCAD CLI-based snapshot command**, because it aligns with the established architectural decision (ADR-004) to use OpenSCAD as the universal compilation target, requires no additional dependencies beyond the existing OpenSCAD installation, and provides proven rendering quality with comprehensive camera control.

### Command Interface

```
solid <path> snapshot [options]
```

**Required Options:**
- `--output PATH` or `-o PATH`: Output file path (default: `snapshot.png` in current directory)
- `--time FLOAT`: Animation time value for AssemblyNode (0.0 to 1.0, default: 0.0)

**Camera Options (OpenSCAD `--camera` parameter):**
- `--camera SPEC`: Camera specification in OpenSCAD format
  - Gimbal format: `translate_x,y,z,rot_x,y,z,dist` (Euler angles with translation and distance)
  - Vector format: `eye_x,y,z,center_x,y,z` (Eye position and look-at center)
- `--autocenter`: Adjust camera to look at object's center
- `--viewall`: Adjust camera to fit object in view

**Image Options:**
- `--imgsize WxH`: Image dimensions (default: `1920x1080`)
- `--projection (ortho|perspective)`: Projection mode (default: `perspective`)
- `--colorscheme NAME`: Color scheme (default: `Cornfield`)
  - Available: Cornfield, Metallic, Sunset, Starnight, BeforeDawn, Nature, DeepOcean, Solarized, Tomorrow, Tomorrow Night, Monotone

**Render Mode:**
- `--render`: Full geometry evaluation (slower but accurate, default)
- `--preview`: ThrownTogether preview (faster, may show artifacts)

**View Helpers:**
- `--view ITEMS`: Comma-separated view options: axes, crosshairs, edges, scales, wireframe

### Implementation Architecture

The `Snapshot` command will follow the established manager pattern:

```
solid_node/
  manager/
    __init__.py
    develop.py
    test.py
    snapshot.py    # New file
```

The implementation will:
1. Load the node using existing `load_node()` infrastructure
2. For AssemblyNode with `--time`, call `set_keyframe(time)` before rendering
3. Invoke `node.assemble()` to ensure SCAD file is generated
4. Execute OpenSCAD CLI to render the SCAD file to PNG

```python
# Core rendering logic (simplified)
from subprocess import run

def render_snapshot(node, output_path, camera, imgsize, **options):
    cmd = ['openscad', '-o', output_path]

    if camera:
        cmd.extend(['--camera', camera])
    if imgsize:
        cmd.extend(['--imgsize', imgsize])
    if options.get('autocenter'):
        cmd.append('--autocenter')
    if options.get('viewall'):
        cmd.append('--viewall')
    # ... additional options

    cmd.append(node.scad_file)
    run(cmd, check=True)
```

### Example Usage

```bash
# Basic snapshot with default camera
solid root snapshot -o model.png

# Animation frame at time=0.5
solid robot_arm snapshot --time 0.5 -o frame_50.png

# Custom camera angle (gimbal format)
solid gear_assembly snapshot --camera 0,0,0,45,0,30,100 -o isometric.png

# Auto-fit view with orthographic projection
solid bracket snapshot --viewall --autocenter --projection ortho -o top_view.png

# High-resolution render for documentation
solid housing snapshot --imgsize 3840x2160 --colorscheme Metallic -o hero.png

# Quick preview for iteration
solid prototype snapshot --preview --viewall -o quick_check.png
```

## Pros and Cons of the Options

### OpenSCAD CLI-based snapshot command

- **Good**: Zero additional dependencies (OpenSCAD already required by ADR-004)
- **Good**: Consistent rendering with OpenSCAD viewer used in `develop --openscad`
- **Good**: Mature, well-tested rendering pipeline
- **Good**: Comprehensive camera control with industry-standard parameters
- **Good**: Natural fit with existing SCAD file generation pipeline
- **Good**: Works with all CAD backends (SolidPython2, CadQuery, JSCAD) via OpenSCAD compilation
- **Bad**: Rendering speed limited by OpenSCAD performance
- **Bad**: No interactive camera positioning (agents must specify camera programmatically)
- **Bad**: Color/material options limited to OpenSCAD color schemes
- **Bad**: Requires OpenSCAD to be installed and accessible in PATH

### Headless browser capture of web viewer

- **Good**: Could reuse existing Three.js rendering code
- **Good**: Better material/lighting options than OpenSCAD
- **Bad**: Requires headless browser (Puppeteer/Playwright) - significant new dependency
- **Bad**: Complex setup for headless rendering
- **Bad**: Slower startup time due to browser initialization
- **Bad**: Fragile due to browser/WebGL compatibility issues

### Custom OpenGL/Three.js headless renderer

- **Good**: Full control over rendering pipeline
- **Good**: Could match web viewer exactly
- **Bad**: Significant implementation effort
- **Bad**: New dependency on headless OpenGL (osmesa, EGL)
- **Bad**: Platform-specific issues with GPU/software rendering
- **Bad**: Duplicates rendering code (violates DRY)

### CadQuery/OCP-based rendering

- **Good**: High-quality BREP rendering
- **Good**: Better for CadQuery-native models
- **Bad**: Only works for CadQuery backend, not SolidPython2 or JSCAD
- **Bad**: Breaks architectural consistency (ADR-004 mandates OpenSCAD as universal target)
- **Bad**: Additional heavy dependency (OCP)

## Consequences

### Positive

- **Enables agent autonomy**: AI agents can now see their work, completing the feedback loop for autonomous CAD development
- **Consistent architecture**: Uses established OpenSCAD compilation target pattern
- **Minimal footprint**: No new dependencies; leverages existing OpenSCAD installation
- **Animation verification**: Agents can render animation frames via `--time` parameter
- **Documentation generation**: Snapshot command useful for generating project documentation images
- **Scriptable workflows**: Enables batch rendering, automated documentation, CI/CD visual regression testing

### Negative

- **OpenSCAD dependency strengthened**: Snapshot requires OpenSCAD even if project uses other CAD backends
- **Rendering limitations**: Bound by OpenSCAD's rendering capabilities (no PBR materials, limited lighting)
- **No real-time feedback**: Each snapshot is a discrete render; no live preview capability
- **Camera learning curve**: Agents must learn OpenSCAD camera coordinate system

### Neutral

- **New manager module**: Adds `snapshot.py` to manager namespace, following established pattern
- **CLI complexity growth**: Adds another subcommand with many options (but consistent with OpenSCAD CLI)

## Future Considerations

1. **Batch rendering**: A future enhancement could add `--animation-frames N` to render entire animation sequences
2. **Camera presets**: Named presets (isometric, front, top, etc.) could simplify common use cases
3. **STL-based rendering**: If OpenSCAD rendering proves limiting, a future ADR could evaluate Three.js server-side rendering as an alternative
4. **Visual regression testing**: The snapshot command could integrate with the test framework for visual assertion capabilities

## References

- solid-node/solid_node/viewers/openscad.py (existing OpenSCAD integration)
- solid-node/solid_node/cli.py (CLI registration pattern)
- solid-node/solid_node/manager/develop.py (manager command pattern)
- solid-node/solid_node/manager/test.py (manager command pattern)
- OpenSCAD CLI documentation: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Using_OpenSCAD_in_a_command_line_environment
