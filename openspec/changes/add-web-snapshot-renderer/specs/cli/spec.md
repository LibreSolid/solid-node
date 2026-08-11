## MODIFIED Requirements

### Requirement: Snapshot command

The system SHALL provide `solid snapshot <path>` rendering a PNG, with options:
`-o/--output` (default `snapshot.png`), `--time` (0.0–1.0, validated, default
0.0, applied via `set_keyframe`), `--camera` (gimbal or vector spec),
`--autocenter`, `--viewall`, `--imgsize` (default `1920x1080`, validated),
`--projection` (`ortho`|`perspective`), `--colorscheme` (the 11 OpenSCAD
schemes, default Cornfield), mutually exclusive `--render`/`--preview`,
`--view` (comma-separated of axes, crosshairs, edges, scales, wireframe), and
`--renderer` (`openscad`|`web`, default `openscad`).

With `--renderer openscad` the image is produced by the OpenSCAD CLI; without a
`DISPLAY` it SHALL wrap the render under `xvfb-run -a`, and error clearly if
xvfb is also unavailable.

With `--renderer web` the image is produced by the packaged browser viewer with
a transparent background, as specified in the web-snapshot capability, and no
X display is required. `--projection`, `--colorscheme`, `--view`, `--render`,
and `--preview` are OpenSCAD-only: supplying any of them together with
`--renderer web` SHALL fail with an error naming them rather than ignoring
them. Options with renderer-independent meaning — `-o/--output`, `--time`,
`--imgsize`, `--camera` — SHALL behave equivalently under either renderer,
and `--autocenter` and `--viewall` describe what the web renderer does by
default.

#### Scenario: Headless snapshot

- **WHEN** an agent runs `solid snapshot root --time 0.5 -o pose.png` on a
  machine with no X display but xvfb installed
- **THEN** a PNG of the assembly at `$t = 0.5` is written to `pose.png`

#### Scenario: Transparent snapshot for a host

- **WHEN** an agent runs `solid snapshot root --renderer web -o card.png`
- **THEN** a PNG of the assembly with a transparent background is written to
  `card.png`

#### Scenario: An OpenSCAD-only option with the web renderer

- **WHEN** an agent runs `solid snapshot root --renderer web --colorscheme
  Metallic`
- **THEN** the command fails, reporting that `--colorscheme` is not supported
  by the web renderer, and writes no image
