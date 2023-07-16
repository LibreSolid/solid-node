import sys
import bdb
import time
import traceback
from termcolor import colored
from solid_node.core.loader import load_test

class Test:
    """Run a node's tests"""

    fail_fast = False
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
                    try:
                        test_steps = self.test_case.test_steps
                    except:
                        test_steps = node.test_steps
                    error = None
                    for step in range(test_steps):
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
                        num_passed += 1
                    else:
                        sys.stdout.write(colored('FAIL!\n', 'red'))
                        print(error[2])
                        num_failed += 1
                finally:
                    if hasattr(self.test_case, "tearDown"):
                        self.test_case.tearDown()

        if hasattr(self.test_case, "tearDownClass"):
            self.test_case.tearDownClass()

        end_time = time.time()
        total_time = end_time - start_time
        sys.stdout.write(f"\nRan {num_tests} tests in {total_time:.2f} seconds: {num_passed} passed, {num_failed} failed\n")
