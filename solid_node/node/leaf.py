from .base import AbstractBaseNode


class LeafNode(AbstractBaseNode):
    """This is a base class for all leaf nodes, which are nodes
    that generate solid structures.
    Each LeafNode subclass uses a different technology to generate
    a solid, and outputs the result as STL.
    LeafNode subclasses are in the solid_node.node.adapters.* namespace.
    """

    _type = 'LeafNode'

    @property
    def time(self):
        """Raise an exception, as leaf nodes cannot rely on time.
        Implementing a FlexibleNode is in the roadmap"""
        raise Exception(f"Leaf node cannot rely on time, animation should be "
                        "done on internal nodes")

    @property
    def children(self):
        """Returns an empty tuple, as leaf nodes have no children"""
        return tuple()

    def as_scad(self, rendered):
        """Internally, the project is composed using OpenScad to render
        all STLs, so each LeafNode subclass must be able to output
        scad code"""
        raise NotImplementedError(f"LeafNode subclass {self.__class__} must "
                                  "be able to output scad")

    @property
    def namespace(self):
        """Each LeafNode subclass must declare a namespace, and objects
        returned by render() must belong to that namespace"""
        raise NotImplementedError(f"LeafNode needs to belong to a namespace-"
                                  "constrained class.")

    def validate(self, rendered):
        """Check if rendered result is an object of proper namespace"""
        if type(rendered) in (list, tuple):
            raise Exception(f"{self.__class__} is a LeafNode and should return "
                            f"a {self.namespace} object, not a list")

        if not type(rendered).__module__.startswith(self.namespace):
            raise Exception(f"{self.__class__} is a LeafNode and should render "
                            f"as {self.namespace} child, not {type(rendered)}")
