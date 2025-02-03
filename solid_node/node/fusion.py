from .internal import InternalNode


class FusionNode(InternalNode):
    """
    Represents a fusion of components into a single, inseparable unit.
    This is an internal node that can contain instances of LeafNode or other internal nodes.
    The render method of this class returns a list of its child nodes.
    """

    _type = 'FusionNode'

    @property
    def time(self):
        raise Exception(f"FusionNode cannot rely on time, use AssemblyNode for animation")
