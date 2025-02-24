from .internal import InternalNode


class FusionNode(InternalNode):
    """
    Represents a fusion of components into a single, inseparable unit.
    This is an internal node that can contain instances of LeafNode or other FusionNode.
    The render method of this class returns a list of its child nodes.
    """

    _type = 'FusionNode'

    @property
    def time(self):
        """You can't use self.time with a FusionNode, as the resulting object
        is expected to be rigid."""
        raise Exception(f"FusionNode cannot rely on time, use AssemblyNode for animation")
