import React, { useRef, useState,  } from 'react';
import * as THREE from 'three';
import logo from './logo.svg';
import './App.css';
import { Resizable } from 're-resizable';
import { STLViewer, STLViewerHandles } from './viewer/STLViewer';
import ControlCube from './viewer/ControlCube';

function App() {
  const stlViewerRef = useRef<STLViewerHandles | null>(null);
  const [rotation, setRotation] = useState<THREE.Vector3>(new THREE.Vector3(0, 0, 100));

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
          <STLViewer rotation={rotation} ref={stlViewerRef} stlPath="/demo.stl" />
          <div style={{position: 'relative'}}>
            <ControlCube
              onRotate={setRotation}
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
