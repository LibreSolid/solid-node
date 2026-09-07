"""Audit probes: create temporary projects, print observed behavior, and clean up.
Run with the project development environment; see README.md.
"""
import asyncio
import contextlib
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
ENV=dict(os.environ,PYTHONPATH=str(REPO),PYTHONDONTWRITEBYTECODE='1'); ENV.pop('SOLID_BUILD_DIR',None)
CMD=[sys.executable,'-c','from solid_node.cli import manage; manage()']
RESULTS={}
def cli(root,*args):
    return subprocess.run(CMD+list(args),cwd=root,env=ENV,capture_output=True,text=True,timeout=90)
def project(root,code,manifest='model = "design.part:Part"'):
    (root/'pyproject.toml').write_text('[tool.solid-node]\n'+manifest+'\n')
    (root/'design').mkdir(); (root/'design/__init__.py').write_text('')
    (root/'design/part.py').write_text(code)
GOOD='from solid_node.node import Solid2Node\nfrom solid2 import cube\nclass Part(Solid2Node):\n    def render(self):\n        return cube(1)\n'
with tempfile.TemporaryDirectory(prefix='solid-audit-more-') as directory:
    base=Path(directory)
    root=base/'export';root.mkdir();project(root,GOOD)
    nested=root/'design/nested';nested.mkdir()
    output=base/'exports/sub/portable'
    result=cli(nested,'export',str(root/'design/part.py'),'--no-widget','-o',str(output))
    manifest=json.loads((output/'manifest.json').read_text())
    target=(output/manifest['root']['model']).resolve()
    RESULTS['export_escape']=dict(exitcode=result.returncode,model=manifest['root']['model'],outside_output=not target.is_relative_to(output),target_exists=target.exists(),target=str(target.relative_to(base)))

    root=base/'zero';root.mkdir();project(root,GOOD+'\nfrom solid_node.node import AssemblyNode\nfrom solid_node.parameters import Count\nclass Rack(AssemblyNode):\n    count = Count(0, min=0)\n    parts = Part().repeat(count)\n','model = "design.part:Rack"')
    result=cli(root,'build')
    RESULTS['zero_children']=dict(exitcode=result.returncode,stderr=result.stderr[-1800:])

    root=base/'all';root.mkdir();project(root,GOOD+'\nclass Broken(Solid2Node):\n    def render(self):\n        raise RuntimeError("intentional broken first model")\n','[tool.solid-node.models]\nbroken = "design.part:Broken"\ngood = "design.part:Part"')
    (root/'design/test_part.py').write_text('from solid_node.test import TestCase\nfrom .part import Part\nclass PartTest(TestCase):\n    node = Part\n    def test_marker(self):\n        print("AUDIT_SECOND_MODEL_RAN")\n')
    result=cli(root,'test','--all')
    RESULTS['test_all']=dict(exitcode=result.returncode,second_ran='AUDIT_SECOND_MODEL_RAN' in result.stdout+result.stderr,stdout=result.stdout,stderr=result.stderr[-1400:])

    # A real exact producer writes while another process owns its build lock.
    root=base/'lock';root.mkdir();project(root,'from solid_node.node import CadQueryNode\nimport cadquery as cq\nclass Part(CadQueryNode):\n    def render(self):\n        return cq.Workplane("XY").box(1, 1, 1)\n')
    with (root/'_build.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with (base/'lock-output.log').open('w+') as logfile:
            proc=subprocess.Popen(CMD+['build'],cwd=root,env=ENV,stdout=logfile,stderr=logfile)
            try:
                deadline=time.monotonic()+30
                stls=[]
                while time.monotonic()<deadline and proc.poll() is None:
                    stls=list(root.glob('_build/**/*.stl'))
                    if stls:break
                    time.sleep(.1)
                RESULTS['lock_bypass']=dict(stl_written_while_locked=bool(stls),child_still_running=proc.poll() is None,stl_sizes=[p.stat().st_size for p in stls])
            finally:
                fcntl.flock(lock,fcntl.LOCK_UN)
                RESULTS['lock_bypass']['exitcode']=proc.wait(timeout=45)

    # Numeric-time validation, exercised on a real project node.
    root=base/'sim';root.mkdir();project(root,'from solid_node.node import AssemblyNode\nfrom solid_node.simulation import Driver, Instruction\nclass Part(AssemblyNode):\n    x = Driver(default=0)\n    instructions={"Jump": Instruction({"x": 10}, duration=0)}\n    def render(self):\n        return []\n')
    from solid_node.core.loader import load_node
    with contextlib.chdir(root):
        # Keep the module distinct from packages loaded elsewhere in this process.
        node=load_node()
        from solid_node.simulation import Sim
        sim=Sim(node,dt=-.1); called=[]
        sim.at(.1).run(lambda s:called.append(s.tick))
        sim.run(1)
        RESULTS['negative_dt']=dict(tick=sim.tick,checks_run=len(called),scheduled=sorted(sim._at))
        sim=Sim(node,dt=.1);sim.trigger('Jump');sim.run(0)
        RESULTS['zero_instruction']=dict(state_at_trigger=sim.state,node_x=node.x)
print(json.dumps(RESULTS,indent=2))
