from .base import AbstractBaseNode
from solid2 import union

class InternalNode(AbstractBaseNode):

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


class FusionNode(InternalNode):

    @property
    def time(self):
        raise Exception(f"FusionNode cannot rely on time, use AssemblyNode for animation")


class AssemblyNode(InternalNode):

    @property
    def time(self):
        """The $t variable, the animation time from 0 to 1"""
        self.rigid = False
        return get_animation_time()
