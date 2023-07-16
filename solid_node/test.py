import re
import inspect
from unittest import TestCase as BaseTestCase
from solid_node.node.base import StlRenderStart


def get_node_file(path):
    path = path.split('/')
    test_file = path.pop()
    if not test_file.startswith('test_'):
        raise Exception("Test file should start with test_")
    path.append(test_file[5:])  # remove test_ prefix
    return '/'.join(path)


def build_stls(node):
    while True:
        try:
            node.trigger_stl()
            return
        except StlRenderStart as job:
            job.wait()



class TestCase(BaseTestCase):

    def setUpClass(self):
        from solid_node.node.internal import InternalNode
        # Set node property on test instance
        node = self.__load_node()
        self.node = node
        # Set an alias convert CamelCase class to snake_case attribute
        attr_name = re.sub(
            r'(?<=[a-z])(?=[A-Z])', '_',
            self.__class__.__name__,
        ).lower().replace('_test', '')

        setattr(self, attr_name, node)

        rendered = node.render()
        node.assemble()

        build_stls(node)

        if issubclass(node.__class__, InternalNode):
            self.children = rendered
        else:
            self.children = tuple()

    def __load_node(self):
        # avoid circular import
        from solid_node.core import load_node
        path = inspect.getfile(self.__class__)
        node_file = get_node_file(path)
        return load_node(node_file)
