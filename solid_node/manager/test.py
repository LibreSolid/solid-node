import traceback
import sys
import time
from termcolor import colored
from solid_node.core.loader import load_test

class Test:
    """Run a node's tests"""

    def add_arguments(self, parser):
        pass


    def handle(self, args):
        self.test_case = load_test(args.path)
        self.run_tests()

    def run_tests(self):
        num_tests = 0
        num_passed = 0
        num_failed = 0
        start_time = time.time()

        self.test_case.setUpClass()

        node = self.test_case.node

        for method_name in dir(self.test_case):
            if method_name.startswith("test"):
                num_tests += 1
                method = getattr(self.test_case, method_name)
                try:
                    if hasattr(self.test_case, "setUp"):
                        self.test_case.setUp()
                    sys.stdout.write(f"Running {method_name}")
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
                        except Exception as e:
                            error = e
                            step_fail += 1
                            dot_color = 'red'
                        sys.stdout.write(colored('.', dot_color))
                        sys.stdout.flush()
                    if not step_fail:
                        sys.stdout.write(colored(" passed\n", "green"))
                        num_passed += 1
                    else:
                        try:
                            raise error
                        except Exception as e:
                            traceback.print_exc()
                            sys.stdout.write("\n")
                            sys.stdout.write(colored(f" {method_name} failed: {e}\n", "red"))
                        num_failed += 1
                finally:
                    if hasattr(self.test_case, "tearDown"):
                        self.test_case.tearDown()

        if hasattr(self.test_case, "tearDownClass"):
            self.test_case.tearDownClass()

        end_time = time.time()
        total_time = end_time - start_time
        sys.stdout.write(f"\nRan {num_tests} tests in {total_time:.2f} seconds: {num_passed} passed, {num_failed} failed\n")
