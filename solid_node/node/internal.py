from .base import AbstractBaseNode
from solid2 import union, get_animation_time


class InternalNode(AbstractBaseNode):
    """Internal nodes combine its leaf nodes in some way to make
    a node with several solids."""

    @property
    def time(self):
        raise NotImplementedError(f"InternalNode subclass {self.__class__} "
                                  "must deal with animation time")

    def as_scad(self, children):
        self.children = children

        scads = []

        for child in children:
            scads.append(child.assemble(self.root))
            self.files.update(child.files)
            self.rigid = self.rigid and child.rigid

        if len(scads) > 1:
            rendered = union()(scads)
        else:
            rendered = scads[0]

        return rendered

    def validate(self, rendered):
        if type(rendered) not in (list, tuple):
            raise Exception(f"{self.__class__}.render() should return a list, "
                            f"not {type(rendered)}")

        for child in rendered:
            if not issubclass(type(child), AbstractBaseNode):
                raise Exception(f"{self.__class__}.render() returned invalid "
                                f"type {type(child)}")
            if type(child) is type(self):
                raise Exception(f"{self.__class__}.render() cannot return its "
                                "own type")
