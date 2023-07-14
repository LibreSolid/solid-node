from .base import AbstractBaseNode
from .spatial import SpatialNodeMixin


class LeafNode(AbstractBaseNode, SpatialNodeMixin):

    @property
    def time(self):
        raise Exception(f"Leaf node cannot rely on time, animation should be "
                        "done on internal nodes")

    @property
    def children(self):
        return tuple()

    @property
    def as_scad(self, rendered):
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
                            f"as {self.namespace} child, not {type(child)}")

    def collect_files(self):
        pass
