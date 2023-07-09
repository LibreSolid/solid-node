import os
import re
import sys
import shutil
from .base import BaseNodeTest, preserve
from . import flat_project, deep_project


class ScadSavingTest(BaseNodeTest):

    def setUp(self):
        super().setUp()
        self.solid = flat_project.SimpleCylinder()
        self.solid.assemble()

    def test_scad_file_is_saved(self):
        self.assertTrue(os.path.exists(self.solid.scad_file))

    def test_scad_file_is_inside_build_dir(self):
        rel_path = os.path.relpath(self.solid.scad_file,
                                   self.build_dir)

        self.assertFalse(rel_path.startswith('..'))


class FlatTest:
    models = [
        flat_project.SimpleCylinder,
        flat_project.SimplePipe,
        flat_project.TwoCylinders,
        flat_project.TwoCylindersTwice,
        flat_project.ThirdLevel,
    ]


class FlatScadTest(BaseNodeTest, FlatTest):

    def test_simple_cylinder(self):
        self.load_solid(0)
        self.assertCode("""
        cylinder(h = 10, r = 1);
        """)

    def test_simple_pipe(self):
        self.load_solid(1)
        self.assertCode("""
        difference() {
            cylinder(h = 100, r = 10);
            cylinder(h = 100, r = 8);
        }
        """)

    def test_two_cylinders(self):
        self.load_solid(2)
        self.assertCode("""
        union() {
            cylinder(h = 5, r = 10);
            cylinder(h = 10, r = 5);
        }
        """)

    def test_two_cylinders_twice(self):
        self.load_solid(3)
        self.assertCode("""
        union() {
            union() {
                cylinder(h = 5, r = 10);
                cylinder(h = 10, r = 5);
            }
            rotate(a = 180, v = [1, 0, 0]) {
                union() {
                    cylinder(h = 5, r = 10);
                    cylinder(h = 10, r = 5);
                }
            }
        }
        """)

    def test_third_level(self):
        self.load_solid(4)
        self.assertCode("""
        union() {
            union() {
                union() {
                    cylinder(h = 5, r = 10);
                    cylinder(h = 10, r = 5);
                }
                rotate(a = 180, v = [1, 0, 0]) {
                    union() {
                        cylinder(h = 5, r = 10);
                        cylinder(h = 10, r = 5);
                    }
                }
            }
            rotate(a = 180, v = [0, 1, 0]) {
                union() {
                    union() {
                        cylinder(h = 5, r = 10);
                        cylinder(h = 10, r = 5);
                    }
                    rotate(a = 180, v = [1, 0, 0]) {
                        union() {
                            cylinder(h = 5, r = 10);
                            cylinder(h = 10, r = 5);
                        }
                    }
                }
            }
        }
        """)


class FlatStlTest(BaseNodeTest, FlatTest):

    def test_simple_pipe(self):
        # The parent model is not optimized. Should it be?
        self.load_solid(1, 10)
        self.assertCode("""
        difference() {
            cylinder(h = 100, r = 10);
            cylinder(h = 100, r = 8);
        }
        """)

    def test_two_cylinders_first_render(self):
        self.load_solid(2, 1)
        self.assertCode("""
        union() {
            import(file = "simple_cylinder-10,5.stl", origin = [0, 0]);
            cylinder(h = 10, r = 5);
        }
        """)

    def test_two_cylinders_second_render(self):
        self.load_solid(2, 2)
        self.assertCode("""
        union() {
            import(file = "simple_cylinder-10,5.stl", origin = [0, 0]);
            import(file = "simple_cylinder-5,10.stl", origin = [0, 0]);
        }
        """)

    def test_two_cylinders_twice(self):
        # First cylinder is optimized and loaded twice
        self.load_solid(3, 1)
        self.assertCode("""
        union() {
            union() {
                import(file = "simple_cylinder-10,5.stl", origin = [0, 0]);
                cylinder(h = 10, r = 5);
            }
            rotate(a = 180, v = [1, 0, 0]) {
                union() {
                    import(file = "simple_cylinder-10,5.stl", origin = [0, 0]);
                    cylinder(h = 10, r = 5);
                }
            }
        }
        """)

    def test_third_level(self):
        self.load_solid(4, 2)
        self.assertCode("""
        union() {
            union() {
                union() {
                    import(file = "simple_cylinder-10,5.stl", origin = [0, 0]);
                    import(file = "simple_cylinder-5,10.stl", origin = [0, 0]);
                }
                rotate(a = 180, v = [1, 0, 0]) {
                    union() {
                        import(file = "simple_cylinder-10,5.stl", origin = [0, 0]);
                        import(file = "simple_cylinder-5,10.stl", origin = [0, 0]);
                    }
                }
            }
            rotate(a = 180, v = [0, 1, 0]) {
                union() {
                    union() {
                        import(file = "simple_cylinder-10,5.stl", origin = [0, 0]);
                        import(file = "simple_cylinder-5,10.stl", origin = [0, 0]);
                    }
                    rotate(a = 180, v = [1, 0, 0]) {
                        union() {
                            import(file = "simple_cylinder-10,5.stl", origin = [0, 0]);
                            import(file = "simple_cylinder-5,10.stl", origin = [0, 0]);
                        }
                    }
                }
            }
        }
        """)


class DeepStlTest(BaseNodeTest):
    models = [
        deep_project.ThirdLevel,
    ]

    def test_third_level(self):
        self.load_solid(0, 1)
        self.assertCode("""
        union() {
            union() {
                union() {
                    import(file = "one/two/three/simple_cylinder-10,5.stl", origin = [0, 0]);
        cylinder(h = 10, r = 5);
                }
                rotate(a = 180, v = [1, 0, 0]) {
                    union() {
                        import(file = "one/two/three/simple_cylinder-10,5.stl", origin = [0, 0]);
                        cylinder(h = 10, r = 5);
                    }
                }
            }
            rotate(a = 180, v = [0, 1, 0]) {
                union() {
                    union() {
                        import(file = "one/two/three/simple_cylinder-10,5.stl", origin = [0, 0]);
                        cylinder(h = 10, r = 5);
                    }
                    rotate(a = 180, v = [1, 0, 0]) {
                        union() {
                            import(file = "one/two/three/simple_cylinder-10,5.stl", origin = [0, 0]);
                            cylinder(h = 10, r = 5);
                        }
                    }
                }
            }
        }
        """)
