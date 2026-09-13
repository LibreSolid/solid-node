# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import sys
import logging
from subprocess import run, CalledProcessError
from solid_node.core.loader import ProjectManifestError, load_node, select_model
from solid_node.motion.ports import declared_time
from solid_node.core.builder import project_build_lock
from solid_node.viewers.openscad import OpenScadRenderer
from solid_node.openscad import OpenScadUnavailable


logger = logging.getLogger('manager.snapshot')
OPENSCAD_RENDERER = OpenScadRenderer()


class SnapshotOptionError(ValueError):
    """An option names something this node does not have, or something a
    still image cannot be posed by."""


# OpenSCAD color schemes
COLORSCHEMES = [
    'Cornfield', 'Metallic', 'Sunset', 'Starnight', 'BeforeDawn',
    'Nature', 'DeepOcean', 'Solarized', 'Tomorrow', 'Tomorrow Night', 'Monotone'
]

# View helper options
VIEW_OPTIONS = ['axes', 'crosshairs', 'edges', 'scales', 'wireframe']


class Snapshot:
    """Renders a node to a PNG image, through the OpenSCAD CLI by default
    or through the browser viewer with --renderer web for a transparent
    background. Enables AI agents to visually inspect their work without
    human intervention."""

    needs_node = True

    def add_arguments(self, parser):
        parser.add_argument(
            '--renderer', choices=['openscad', 'web'], default='openscad',
            help='Image renderer (default: openscad)',
        )
        # Output options
        parser.add_argument(
            '-o', '--output',
            type=str,
            default=None,
            help='Output file path (default: derived from the node reference)'
        )

        # Animation time
        parser.add_argument(
            '--time',
            type=float,
            default=0.0,
            help='Animation time value for AssemblyNode (0.0 to 1.0, default: 0.0)'
        )

        # Camera options
        parser.add_argument(
            '--camera',
            type=str,
            help='Camera specification in OpenSCAD format. '
                 'Gimbal: translate_x,y,z,rot_x,y,z,dist or '
                 'Vector: eye_x,y,z,center_x,y,z'
        )
        parser.add_argument(
            '--autocenter',
            action='store_true',
            help='Adjust camera to look at object center'
        )
        parser.add_argument(
            '--viewall',
            action='store_true',
            help='Adjust camera to fit object in view'
        )

        # Image options
        parser.add_argument(
            '--imgsize',
            type=str,
            default='1920x1080',
            help='Image dimensions as WxH (default: 1920x1080)'
        )
        parser.add_argument(
            '--projection',
            type=str,
            choices=['ortho', 'perspective'],
            default=None,
            help='Projection mode (default: perspective)'
        )
        parser.add_argument(
            '--colorscheme',
            type=str,
            choices=COLORSCHEMES,
            default=None,
            help='Color scheme (default: Cornfield)'
        )

        # Render mode
        render_group = parser.add_mutually_exclusive_group()
        render_group.add_argument(
            '--render',
            action='store_true',
            default=False,
            help='Full render (OpenSCAD default, slower but accurate)'
        )
        render_group.add_argument(
            '--preview',
            action='store_true',
            help='ThrownTogether preview (faster, may show artifacts)'
        )

        # View helpers
        parser.add_argument(
            '--view',
            type=str,
            help=f'Comma-separated view options: {", ".join(VIEW_OPTIONS)}'
        )

        # Drivers. Distinct from --set, which reaches the root's declared
        # PARAMETERS: a driver is not a parameter and a parameter is not a
        # driver, and a driver-declaring project could not be posed for a
        # still at all before this.
        parser.add_argument(
            '--drive',
            action='append',
            metavar='NAME=VALUE',
            help='Bind a declared driver by its qualified id before the '
                 'image is taken; repeatable'
        )

    def handle(self, args):
        """Main entry point for the snapshot command."""
        try:
            selection = select_model(args.path)
        except ProjectManifestError as error:
            sys.stderr.write(f'Error: {error}\n')
            raise SystemExit(1)
        selection.anchor()
        self.path = selection.reference
        self.overrides = list(getattr(args, 'set', None) or [])
        self.drives = list(getattr(args, 'drive', None) or [])
        self.output = args.output
        self.time = args.time
        renderer = getattr(args, 'renderer', 'openscad')

        if renderer == 'web':
            unsupported = [
                option for option, supplied in (
                    ('--projection', args.projection is not None),
                    ('--colorscheme', args.colorscheme is not None),
                    ('--view', args.view is not None),
                    ('--render', args.render),
                    ('--preview', args.preview),
                ) if supplied
            ]
            if unsupported:
                sys.stderr.write(
                    'Error: the web renderer does not support: '
                    f'{", ".join(unsupported)}\n'
                )
                raise SystemExit(1)

        # Validate time parameter
        if not 0.0 <= self.time <= 1.0:
            sys.stderr.write(f"Error: --time must be between 0.0 and 1.0, got {self.time}\n")
            sys.exit(1)

        # Validate view options if provided
        if args.view:
            view_items = [v.strip() for v in args.view.split(',')]
            invalid = [v for v in view_items if v not in VIEW_OPTIONS]
            if invalid:
                sys.stderr.write(f"Error: Invalid view options: {invalid}. "
                               f"Valid options are: {VIEW_OPTIONS}\n")
                sys.exit(1)

        # Validate imgsize format
        if not self._validate_imgsize(args.imgsize):
            sys.stderr.write(f"Error: Invalid --imgsize format '{args.imgsize}'. "
                           f"Expected WxH (e.g., 1920x1080)\n")
            sys.exit(1)

        # Load and prepare the node
        try:
            node = self._load_and_prepare_node()
            if self.output is None:
                self.output = f'{node.__class__.__name__.lower()}.png'
        except SnapshotOptionError as error:
            sys.stderr.write(f'Error: {error}\n')
            sys.exit(1)
        except Exception as e:
            sys.stderr.write(f"Error loading node: {e}\n")
            sys.exit(1)

        if renderer == 'web':
            from solid_node.viewers.browser import (
                BrowserRenderer, BrowserSnapshotError,
            )
            try:
                BrowserRenderer().render(node, args, self.output)
            except (BrowserSnapshotError, ValueError) as error:
                sys.stderr.write(f'Error: {error}\n')
                raise SystemExit(1)
            print(f"Snapshot saved to {self.output}")
            return

        # Execute OpenSCAD
        try:
            OPENSCAD_RENDERER.render(node, args, self.output, run)
            print(f"Snapshot saved to {self.output}")
        except CalledProcessError as e:
            sys.stderr.write(f"OpenSCAD rendering failed:\n{e.stderr}\n")
            sys.exit(1)
        except FileNotFoundError:
            sys.stderr.write("Error: OpenSCAD not found in PATH. "
                           "Please install OpenSCAD and ensure it is accessible.\n")
            sys.exit(1)
        except OpenScadUnavailable as error:
            sys.stderr.write(f'Error: {error}\n')
            raise SystemExit(1)

    def _validate_imgsize(self, imgsize):
        """Validate image size format (WxH)."""
        try:
            parts = imgsize.lower().split('x')
            if len(parts) != 2:
                return False
            width, height = int(parts[0]), int(parts[1])
            return width > 0 and height > 0
        except (ValueError, IndexError):
            return False

    def _load_and_prepare_node(self):
        """Load the node, pose its named drivers, and prepare it for
        rendering."""
        with project_build_lock():
            node = load_node(self.path,
                             overrides=getattr(self, 'overrides', None))
            self._drive(node)
            # set_keyframe is a no-op for non-animated nodes. --time is a
            # position on the 0..1 timeline under either renderer; a root
            # declaring a time base is keyframed at the seconds that
            # position means, so the image shows what the slider shows.
            base = declared_time(type(node))
            loop = base.loop if base is not None else None
            if base is not None and base.mode == 'running' and self.time:
                raise SnapshotOptionError(
                    f'--time {self.time} names a position on an animation '
                    f'timeline, and {type(node).__name__} declares '
                    f'time = Time.running(): elapsed simulation seconds '
                    f'never wrap, so there is no timeline to be a position '
                    f'on and the document publishes no loop. Pose it with '
                    f'--drive NAME=VALUE instead, which gives the REST '
                    f'POSE at those driver values -- the state a '
                    f'simulation itself starts from.')
            node.set_keyframe(self.time * loop if loop is not None
                              else self.time)
            node.assemble()

        return node

    def _drive(self, node):
        """Bind each `--drive NAME=VALUE` through `set_state`.

        A DECLARED DRIVER only. A joint coordinate of a running root is
        refused by name rather than accepted and lost: `set_state` takes
        one under that base (the run's own door), and with no run to own
        it the enumeration that binding runs immediately recomputes the
        coordinate from the drivers, so the requested value would be
        silently discarded.
        """
        requested = getattr(self, 'drives', None)
        if not requested:
            return
        from solid_node.simulation.enumeration import qualified_drivers

        declared = qualified_drivers(node)
        state = {}
        for entry in requested:
            name, separator, text = entry.partition('=')
            if not separator:
                raise SnapshotOptionError(
                    f"--drive {entry!r} states no value: a driver is posed "
                    f'as --drive NAME=VALUE.')
            name = name.strip()
            if name not in declared:
                self._refuse_driver(node, name, declared)
            try:
                state[name] = float(text)
            except ValueError:
                raise SnapshotOptionError(
                    f"--drive {name}={text!r} is not a number. A driver's "
                    f'value is a plain number in its native '
                    f'unit.') from None
        node.set_state(**state)

    def _refuse_driver(self, node, name, declared):
        known = ', '.join(sorted(declared)) or 'none'
        base = declared_time(type(node))
        if base is not None and base.mode == 'running':
            from solid_node.simulation.program import qualified_coordinates

            if name in qualified_coordinates(node):
                raise SnapshotOptionError(
                    f"--drive names '{name}', which is a JOINT COORDINATE "
                    f'the run owns rather than a declared driver. A '
                    f"coordinate's value is what the run makes of it: with "
                    f'no run to own it, the enumeration that binding runs '
                    f'recomputes it from the drivers and the value is lost. '
                    f'Ask for the drivers instead -- {known} -- or drive '
                    f'the machine in a scenario or in the browser.')
        raise SnapshotOptionError(
            f"--drive names '{name}', which no node of this tree declares "
            f'as a driver. The drivers it publishes are: {known}.')
