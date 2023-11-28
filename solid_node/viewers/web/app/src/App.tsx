import React, { useRef, useState, useEffect } from 'react';
import * as THREE from 'three';
import './App.css';
import { Resizable } from 're-resizable';
import { STLViewer, STLViewerHandles } from './viewer/STLViewer';
//import { ControlCube } from './viewer/ControlCube';
import { NodeLoader } from './loader';
import { RotationControl } from './viewer/viewer.d';
import { BrowserRouter as Router } from 'react-router-dom';
import CodeEditor from './CodeEditor';
import NavigationTree from './NavigationTree';

const App = () => {
  const stlViewerRef = useRef<STLViewerHandles | null>(null);
  //const [control, setControl] = useState<number>(0);
  const [error, setError] = useState<string>('');
  const [loader, setLoader] = useState<NodeLoader>();
  const [rotation, setRotation] = useState<RotationControl>({
    source: 0,
    rotation: new THREE.Vector3(0, 0, 100),
  });

  if (!loader) {
    setLoader(new NodeLoader(
      window.location.href,
      setError,
    ));
  }

  useEffect(() => {
    loader?.watch();
  }, [loader]);

  /*
  const handleViewerResize = () => {
    stlViewerRef.current?.handleResize();
  };
  */

  const fontSize = 15;
  //const editorWidth = fontSize * 80 / 2;

  return (
    <Router>
      <div className="app">
        <div className="top">
          <Resizable
            defaultSize={{ width: '12%', height: '100%' }}
            className="pane left"
            enable={{ right: true }}
          >
            <NavigationTree/>
          </Resizable>

          <Resizable
            className="pane center"
            defaultSize={{ width: '46.4%', height: '100%' }}
            enable={{ right: true }}
          >
            <CodeEditor
              loader={loader}
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
              loader={loader}
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
