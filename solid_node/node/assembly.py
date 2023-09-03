from solid2 import get_animation_time
from .internal import InternalNode


class AssemblyNode(InternalNode):
    """
    Represents a collection of components that can be moved relative to each other.

    This is an internal node that can contain instances of LeafNode or other internal nodes.

    The render method of this class returns a list of its child nodes.
    """

    rigid = False

    def set_testing_time(self, time):
        """Set a fixed time to run tests"""
        self._time = time

    @property
    def time(self):
        """The $t variable, the animation time from 0 to 1"""
        try:
            return self._time
        except AttributeError:
            return get_animation_time()