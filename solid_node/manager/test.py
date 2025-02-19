import re
import sys
import bdb
import time
import traceback
from termcolor import colored
from solid_node.core.loader import load_test, load_node
from solid_node.test import TestCase

class Test:
    """Nodes may implement tests by inheriting solid_node.test.TestCaseMixin
    and creating test methods starting with test_.
    This command runs Run all tests from a node"""

    def __init__(self):
        self.num_tests = 0
        self.num_passed = 0
        self.num_failed = 0
        self.failfast = False

    def add_arguments(self, parser):
        parser.add_argument('--failfast',
                            action='store_true',
                            help='Stop the test run on the first error.')

    def handle(self, args):
        self.node = self.build_node(args.path)
        self.test_case = load_test(args.path)
        if self.test_case:
            self.test_case.set_node(self.node)
        self.failfast = args.failfast
        self.run_tests()

    def build_node(self, path, time=0):
        node = load_node(path)
        node.set_keyframe(time)
        rendered = node.render()
        node.assemble()
        node.build_stls()
        return node

    def run_tests(self):
        start_time = time.time()

        self.run_class_tests(self.node, self.node)
        if self.test_case:
            self.run_class_tests(self.test_case, self.node)

        end_time = time.time()
        total_time = end_time - start_time
        sys.stdout.write(f"\nRan {self.num_tests} tests in {total_time:.2f} seconds: {self.num_passed} passed, {self.num_failed} failed\n")

    # node is kept as argument to be used for recursion into children later
    def run_class_tests(self, klass, node):
        if hasattr(klass, "setUpClass"):
            klass.setUpClass()

        for method_name in dir(klass):
            if method_name.startswith("test_"):
                method = getattr(klass, method_name)
                if callable(method):
                    self.num_tests += 1
                    self.run_test(klass, method_name, method, node)

        if hasattr(klass, "tearDownClass"):
            klass.tearDownClass()

    def run_test(self, klass, name, method, node):
        node._testMethodName = name
        self.save_children_checkpoints(node)

        try:
            if hasattr(self.test_case, "setUp"):
                self.test_case.setUp()
            try:
                class_name = klass.__name__
            except AttributeError:
                class_name = klass.__class__.__name__
            sys.stdout.write(f"Running {class_name}.{name}")
            sys.stdout.flush()
            step_pass = 0
            step_fail = 0
            error = None
            instants = getattr(method, 'testing_instants', [0])
            for instant in instants:
                try:
                    node.set_keyframe(instant)
                    method()
                    step_pass += 1
                    dot_color = 'green'
                except bdb.BdbQuit:
                    print("Developer quit!")
                    return
                except Exception as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    error = (
                        exc_type,
                        exc_value,
                        "".join(traceback.format_exception(
                            exc_type,
                            exc_value,
                            exc_traceback
                        ))
                    )
                    step_fail += 1
                    dot_color = 'red'
                sys.stdout.write(colored('.', dot_color))
                sys.stdout.flush()
                if self.failfast:
                    break
            if not step_fail:
                sys.stdout.write(colored(" passed\n", "green"))
                self.num_passed += 1
            else:
                sys.stdout.write(colored('FAIL!\n', 'red'))
                print(error[2])
                self.num_failed += 1
        finally:
            if hasattr(self.test_case, "tearDown"):
                self.test_case.tearDown()
            self.restore_children_checkpoints(node)

    def save_children_checkpoints(self, node):
        for child in node.children:
            child.save_checkpoint()

    def restore_children_checkpoints(self, node):
        for child in node.children:
            for operation in child.restore_checkpoint():
                operation.mesh(child.mesh)
