import React, { useRef, useEffect, useImperativeHandle, forwardRef, useState } from 'react';
import * as THREE from 'three';
//import { TrackballControls } from 'three/examples/jsm/controls/TrackballControls';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';


type STLViewerProps = {
  stlPath: string;
  rotation: THREE.Vector3,
};


export interface STLViewerHandles {
  handleResize: () => void;
}


export const STLViewer = forwardRef<STLViewerHandles, STLViewerProps>((props, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer>();
  const cameraRef = useRef<THREE.PerspectiveCamera>();
  const sceneRef = useRef<THREE.Scene>();
  const controlsRef = useRef<OrbitControls>();

  const [size, setSize] = useState<number>(150);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.offsetWidth;
    const height = containerRef.current.offsetHeight;

    if (!sceneRef.current) {
      sceneRef.current = new THREE.Scene();
      sceneRef.current.background = new THREE.Color(0xe5e5e5);

      cameraRef.current = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
      cameraRef.current.position.z = 100;
      cameraRef.current.up.set(0, 0, 1)

      rendererRef.current = new THREE.WebGLRenderer({ antialias: true });
      rendererRef.current.setSize(width, height);
    }

    const scene = sceneRef.current!;
    const camera = cameraRef.current!;
    const renderer = rendererRef.current!;

    if (!containerRef.current.firstChild) {
      containerRef.current.appendChild(renderer.domElement);
    }

    controlsRef.current = new OrbitControls(camera, renderer.domElement);
    const controls = controlsRef.current;

    controls.rotateSpeed = 0.5;
    controls.zoomSpeed = 1;

    // Grid
    const mmGrid = new THREE.GridHelper(size, size, 0xDDDDDD, 0xDDDDDD);
    const cmGrid = new THREE.GridHelper(size, size / 10, 0xBBBBBB, 0xBBBBBB);
    cmGrid.rotation.x = Math.PI / 2;
    mmGrid.rotation.x = Math.PI / 2;

    scene.add(mmGrid);
    scene.add(cmGrid);

    // RGB Axes
    const arrowLength = 50;

    const xAxis = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, 0), arrowLength, 0xff0000);
    const yAxis = new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 0), arrowLength, 0x00ff00);
    const zAxis = new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 0), arrowLength, 0x0000ff);

    scene.add(xAxis);
    scene.add(yAxis);
    scene.add(zAxis);

    const loader = new STLLoader();

    loader.load(props.stlPath, (geometry) => {
      const material = new THREE.MeshNormalMaterial();
      const mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);
      });


    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    return () => {
      renderer.dispose(); // Clean up on component unmount
      window.removeEventListener('resize', handleResize);
    };
  }, [props.stlPath]);

  useEffect(() => {
    if (!cameraRef.current || !props.rotation)
      return;

    const newRotation = props.rotation.clone();
    const scale = cameraRef.current.position.length() / props.rotation.length();

    newRotation.multiplyScalar(scale);

    cameraRef.current.position.copy(newRotation);

  }, [props.rotation, cameraRef.current]);


  const handleResize = () => {
    if (rendererRef.current && containerRef.current && cameraRef.current && sceneRef.current) {
      const width = containerRef.current.offsetWidth;
      const height = containerRef.current.offsetHeight;

      rendererRef.current.setSize(width, height);
      cameraRef.current.aspect = width / height;
      cameraRef.current.updateProjectionMatrix();

      rendererRef.current.render(sceneRef.current, cameraRef.current);
    }
  };

  window.addEventListener('resize', handleResize);

  useImperativeHandle(ref, () => ({
    handleResize
  }));


  return <div ref={containerRef} style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }} />;
});
