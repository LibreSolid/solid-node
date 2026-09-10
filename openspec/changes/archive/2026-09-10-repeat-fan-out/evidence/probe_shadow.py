"""Would a framework-set index/count be visible on a class that declares one?"""
import cadquery as cq
from solid_node.node import CadQueryNode
from solid_node.parameters import Count


class Half(CadQueryNode):
    count = Count(9, min=1)
    index = Count(0, min=0)
    def render(self):
        return cq.Workplane('XY').box(1, 1, 1)


h = Half()
h.__dict__['index'] = 3
h.__dict__['count'] = 2
print('declared index reads:', h.index, ' dict says:', h.__dict__['index'])
print('declared count reads:', h.count, ' dict says:', h.__dict__['count'])
try:
    h.index = 3
except Exception as e:
    print('assignment:', type(e).__name__, e)
