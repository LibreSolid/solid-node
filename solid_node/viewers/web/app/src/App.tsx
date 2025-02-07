import React, { useRef, useState, useEffect } from 'react';
import * as THREE from 'three';
import './App.css';
import { Resizable } from 're-resizable';
import { STLViewer, STLViewerHandles } from './viewer/STLViewer';
//import { ControlCube } from './viewer/ControlCube';
//import { NodeProvider } from './context';
import { RotationControl } from './viewer/viewer.d';
import { BrowserRouter as Router } from 'react-router-dom';
import { Node, Context, loadNode } from './node';
import { Reloader } from './reloader';
import { Animator } from './animator';
import CodeEditor from './CodeEditor';
import NavigationTree from './NavigationTree';


const App = () => {
  const stlViewerRef = useRef<STLViewerHandles | null>(null);
  const [time, setTime] = useState<number>(0);
  const [error, setError] = useState<string>('');
  const [node, setNode] = useState<Node>();
  const [animator, setAnimator] = useState<Animator>();
  const [context, setContext] = useState<Context>({
    time: time,
    setError,
    scene: new THREE.Scene(),
  });
  const [reloader, setReloader] = useState<Reloader>();

  const [rotation, setRotation] = useState<RotationControl>({
    source: 0,
    rotation: new THREE.Vector3(0, 0, 100),
  });

  useEffect(() => {
    if (node) {
      const newContext = Object.assign({}, context, { time });
      node.setContext(newContext);
      setContext(newContext);
      document.title = node.name.replace(/([A-Z])/g, ' $1').trim();
    }
  }, [time, node]);

  useEffect(() => {
    // Avoid react double rendering bug
    if (context.scene.background) return;

    context.scene.background = new THREE.Color(0xe5e5e5);
    const path = window.location.pathname;
    loadNode(path, context).then((node) => {
      setNode(node);
      setAnimator(Animator.getInstance(setTime));
      setReloader(new Reloader(setError, async () => {
        const newNode = await node.reload();
	if (newNode !== undefined) {
	  setNode(newNode);
	}
      }));
    });
  }, []);

  useEffect(() => {
    if (animator) {
      animator.setAnimation(30, 360);
    }
  }, [animator]);

  /*
  const handleViewerResize = () => {
    stlViewerRef.current?.handleResize();
  };
  */

  const fontSize = 15;

  return (
    <Router>
      <div className="app">
        <div className="top">
          <Resizable
            defaultSize={{ width: '12%', height: '100%' }}
            className="pane left"
            enable={{ right: true }}
          >
            <NavigationTree />
          </Resizable>

          <Resizable
            className="pane center"
            defaultSize={{ width: '46.4%', height: '100%' }}
            enable={{ right: true }}
          >
            <CodeEditor
              node={node}
              fontSize={fontSize}
            />
          </Resizable>

          <Resizable
            className="pane right"
            defaultSize={{ width: '41.6%', height: '100%' }}
            enable={{ right: true }}
          >
            {!error &&
              <STLViewer
                controlId={1}
                rotation={rotation}
                context={context}
                setRotation={setRotation}
              />
            }
            {error &&
              <div><pre>{error}</pre></div>
            }
            <div style={{ position: 'relative' }}>
              {/*
              <ControlCube
                controlId={2}
                setControl={setControl}
                rotation={rotation}
                setRotation={setRotation}
              />
              */}
            </div>
          </Resizable>
        </div>

        <Resizable defaultSize={{ width: '100%', height: '30%' }} className="pane bottom">
          <h3>Console</h3>
        </Resizable>
      </div>
    </Router>
  );
}

export default App;
