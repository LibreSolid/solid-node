import re
import sys
import bdb
import time
import traceback
from termcolor import colored
from solid_node.core.loader import load_test, load_node

class Test:
    """Run a node's tests"""

    fail_fast = False

    def __init__(self):
        self.num_tests = 0
        self.num_passed = 0
        self.num_failed = 0

    def add_arguments(self, parser):
        pass

    def handle(self, args):
        self.node = self.build_node(args.path)
        self.test_case = self.build_test_case(args.path)
        self.run_tests()

    def build_node(self, path):
        node = load_node(path)
        node.set_testing_step(0)
        rendered = node.render()
        node.assemble()
        node.build_stls()
        return node

    def build_test_case(self, path):
        test_case = load_test(path)
        test_case.node = self.node

        # Set an alias convert CamelCase class to snake_case attribute
        attr_name = re.sub(
            r'(?<=[a-z])(?=[A-Z])', '_',
            test_case.__class__.__name__,
        ).lower().replace('_test', '')

        setattr(test_case, attr_name, self.node)

        return test_case

    def run_tests(self):
        start_time = time.time()

        self.run_class_tests(self.node, self.node)
        if self.test_case:
            self.run_class_tests(self.test_case, self.node)

        end_time = time.time()
        total_time = end_time - start_time
        sys.stdout.write(f"\nRan {self.num_tests} tests in {total_time:.2f} seconds: {self.num_passed} passed, {self.num_failed} failed\n")

    # node is kept as argument so that we can use for recursion into children later
    def run_class_tests(self, klass, node):
        if hasattr(klass, "setUpClass"):
            klass.setUpClass()

        for method_name in dir(klass):
            if method_name.startswith("test_"):
                method = getattr(klass, method_name)
                if callable(method):
                    self.num_tests += 1
                    self.run_test(method_name, method, node)

        if hasattr(klass, "tearDownClass"):
            klass.tearDownClass()

    def run_test(self, name, method, node):
        try:
            if hasattr(self.test_case, "setUp"):
                self.test_case.setUp()
            sys.stdout.write(f"Running {name}")
            sys.stdout.flush()
            step_pass = 0
            step_fail = 0
            error = None
            for step in range(node.test_steps):
                try:
                    node.set_testing_step(step)
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
                if self.fail_fast:
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
