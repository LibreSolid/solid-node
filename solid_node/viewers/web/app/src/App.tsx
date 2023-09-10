import React, { useRef, useState,  } from 'react';
import * as THREE from 'three';
import './App.css';
import { Resizable } from 're-resizable';
import { STLViewer, STLViewerHandles } from './viewer/STLViewer';
import { ControlCube } from './viewer/ControlCube';
import { RotationControl } from  './viewer/viewer.d';

function App() {
  const stlViewerRef = useRef<STLViewerHandles | null>(null);
  const [rotation, setRotation] = useState<RotationControl>({
    source: 0,
    rotation: new THREE.Vector3(0, 0, 100),
  });
  const [control, setControl] = useState<number>(0);

  const handleViewerResize = () => {
    stlViewerRef.current?.handleResize();
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>

      <Resizable
        defaultSize={{
          width: 50, // default width of the left navigation
          height: '100%'
        }}
        minWidth={100} // minimum width of the left navigation
        maxWidth="50%" // can take up to half of the screen width
        enable={{ top: false, right: true, bottom: false, left: false, topRight: false, bottomRight: false, bottomLeft: false, topLeft: false }}
        onResize={handleViewerResize}
      >
        <nav>
          Navigation
        </nav>
      </Resizable>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>

        <Resizable
          defaultSize={{
            width: '100%',
            height: '80%' // default height of the viewer
          }}
          maxHeight="95%" // can take up to 90% of the screen height
          minHeight="5%" // at least 10% of the screen height
          enable={{ top: false, right: false, bottom: true, left: false, topRight: false, bottomRight: false, bottomLeft: false, topLeft: false }}
          onResize={handleViewerResize}
        >
          <STLViewer
            stlPath="/demo.stl"
            controlId={1}
            rotation={rotation}
            setRotation={setRotation}
          />
          <div style={{position: 'relative'}}>
            <ControlCube
              controlId={2}
              setControl={setControl}
              rotation={rotation}
              setRotation={setRotation}
            />
          </div>
        </Resizable>

        <div style={{ flex: 1 }}>
          {/* Your console content goes here */}
          Console
        </div>
      </div>

    </div>
  );
}

export default App;
