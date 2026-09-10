import cadquery as cq
from solid_node.node import AssemblyNode, CadQueryNode
from solid_node.motion.ports import SignalPort
from solid_node.motion.joints import Prismatic

class Left(CadQueryNode):
    travel = Prismatic(axis=(0,0,1), unit='mm')
    def render(self): return cq.Workplane('XY').box(1,1,1)
class Right(Left):
    pass

def show(label, fn):
    try:
        fn(); print(f'{label}: NO ERROR')
    except Exception as e:
        print(f'{label}: {type(e).__name__}: {e}')

def direct():
    class Rig(AssemblyNode):
        drive = SignalPort()
        plates = [Left(), Right()]
        drive.drives(plates.travel)
show('A. plates.travel in the same body', direct)

def bare():
    class Rig(AssemblyNode):
        drive = SignalPort()
        plates = [Left(), Right()]
        drive.drives(plates)
show('B. drives(plates)', bare)

def nested():
    class Frame(AssemblyNode):
        plates = [Left(), Right()]
    class Rig(AssemblyNode):
        drive = SignalPort()
        frame = Frame()
        drive.drives(frame.plates.travel)
show('C. frame.plates.travel', nested)
