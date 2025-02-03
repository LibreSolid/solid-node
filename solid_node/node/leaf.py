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
        raise Exception(f"Leaf node cannot rely on time, animation should be "
                        "done on internal nodes")

    @property
    def children(self):
        return tuple()

    def as_scad(self, rendered):
        """Internally, the project is composed using OpenScad to render
        all STLs, so each LeafNode subclass must be able to output
        scad code"""
        raise NotImplementedError(f"LeafNode subclass {self.__class__} must "
                                  "be able to output scad")

    @property
    def namespace(self):
        raise NotImplementedError(f"LeafNode needs to belong to a namespace-"
                                  "constrained class.")

    def validate(self, rendered):
        if type(rendered) in (list, tuple):
            raise Exception(f"{self.__class__} is a LeafNode and should return "
                            f"a {self.namespace} object, not a list")

        if not type(rendered).__module__.startswith(self.namespace):
            raise Exception(f"{self.__class__} is a LeafNode and should render "
                            f"as {self.namespace} child, not {type(rendered)}")

    def collect_files(self):
        pass
