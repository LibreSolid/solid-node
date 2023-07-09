from .leaf import LeafNode


class Solid2Node(LeafNode):

    namespace = 'solid2'

    def as_scad(self, rendered):
        return rendered
