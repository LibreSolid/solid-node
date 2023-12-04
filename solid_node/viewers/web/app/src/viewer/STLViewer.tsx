import React, { useRef, useEffect, useImperativeHandle, forwardRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import * as THREE from 'three';
//import { TrackballControls } from 'three/examples/jsm/controls/TrackballControls';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { RotationControl } from  './viewer.d';
import { Context } from '../node';


type STLViewerProps = {
  controlId: number;
  rotation: RotationControl;
  context: Context;
  setRotation: (r: RotationControl) => void;
};


export interface STLViewerHandles {
  handleResize: () => void;
}


export const STLViewer = forwardRef<STLViewerHandles, STLViewerProps>((props, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer>();
  const cameraRef = useRef<THREE.PerspectiveCamera>();
  const controlsRef = useRef<OrbitControls>();
  const location = useLocation();


  const [size, setSize] = useState<number>(150);

  const context = props.context;

  useEffect(() => {
    if (!containerRef.current || !context.scene)
      return;

    const width = containerRef.current.offsetWidth;
    const height = containerRef.current.offsetHeight;

    if (!rendererRef.current) {
      rendererRef.current = new THREE.WebGLRenderer({ antialias: true });
      rendererRef.current.setSize(width, height);
    }

    if (!cameraRef.current) {
      cameraRef.current = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
      cameraRef.current.position.z = 200;
      cameraRef.current.up.set(0, 0, 1);
    }

    const scene = context.scene!;
    const renderer = rendererRef.current!;
    const camera = cameraRef.current!;

    if (!containerRef.current.firstChild) {
      containerRef.current.appendChild(renderer.domElement);
    }

    controlsRef.current = new OrbitControls(camera, renderer.domElement);
    const controls = controlsRef.current;

    controls.rotateSpeed = 0.5;
    controls.zoomSpeed = 1;

    // Grid
    /*
    const mmGrid = new THREE.GridHelper(size, size, 0xDDDDDD, 0xDDDDDD);
    const cmGrid = new THREE.GridHelper(size, size / 10, 0xBBBBBB, 0xBBBBBB);
    cmGrid.rotation.x = Math.PI / 2;
    mmGrid.rotation.x = Math.PI / 2;

    scene.add(mmGrid);
    scene.add(cmGrid);
    */
    // RGB Axes
    /*
    const arrowLength = 50;

    const xAxis = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, 0), arrowLength, 0xff0000);
    const yAxis = new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 0), arrowLength, 0x00ff00);
    const zAxis = new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 0), arrowLength, 0x0000ff);

    scene.add(xAxis);
    scene.add(yAxis);
    scene.add(zAxis);
    */
    const step = 1/2000;

    controls.addEventListener('change', () => {
      props.setRotation({
        source: props.controlId,
        rotation: camera.position.clone(),
      });
    });
    //animate();
    rendererRef.current.render(context.scene, cameraRef.current);
    return () => {
      renderer.dispose(); // Clean up on component unmount
      window.removeEventListener('resize', handleResize);
    };
  }, [context.scene, containerRef.current]);

  useEffect(() => {
    if (!rendererRef.current || !cameraRef.current || !controlsRef.current) {
      return;
    }
    const controls = controlsRef.current;
    const renderer = rendererRef.current;
    const scene = context.scene;
    const camera = cameraRef.current;

    renderer.render(scene, camera);

  }, [context.time, rendererRef.current, cameraRef.current, controlsRef.current]);

  useEffect(() => {
    if (!cameraRef.current || props.rotation?.source === props.controlId)
      return;
    const newRotation = props.rotation.rotation.clone();
    const scale = cameraRef.current.position.length() / props.rotation.rotation.length();

    newRotation.multiplyScalar(scale);

    cameraRef.current.position.copy(newRotation);

  }, [props.rotation, cameraRef.current]);

  const handleResize = () => {
    if (rendererRef.current && containerRef.current && cameraRef.current && context.scene) {
      const width = containerRef.current.offsetWidth;
      const height = containerRef.current.offsetHeight;

      rendererRef.current.setSize(width, height);
      cameraRef.current.aspect = width / height;
      cameraRef.current.updateProjectionMatrix();

      rendererRef.current.render(context.scene, cameraRef.current);
    }
  };

  window.addEventListener('resize', handleResize);

  useImperativeHandle(ref, () => ({
    handleResize
  }));

  return <div ref={containerRef} style={{ position: 'absolute', top: 0, left:0, right: 0, bottom: 0 }} />;
});
