import React, { useRef, useEffect, useImperativeHandle, forwardRef, useState } from 'react';
import * as THREE from 'three';
//import { TrackballControls } from 'three/examples/jsm/controls/TrackballControls';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';
import { RotationControl } from  './viewer.d';

type ControlCubeProps = {
  controlId: number;
  setControl: (controlId: number) => void;
  rotation: RotationControl;
  setRotation: (r: RotationControl) => void;
};


export interface ControlCubeHandles {
}


export const ControlCube = forwardRef<ControlCubeHandles, ControlCubeProps>((props, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer>();
  const cameraRef = useRef<THREE.PerspectiveCamera>();
  const sceneRef = useRef<THREE.Scene>();
  const controlsRef = useRef<OrbitControls>();

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.offsetWidth;
    const height = containerRef.current.offsetHeight;

    if (!sceneRef.current) {
      sceneRef.current = new THREE.Scene();
      sceneRef.current.background = new THREE.Color(0xe5e5e5);

      cameraRef.current = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      cameraRef.current.position.z = 1.5;
      cameraRef.current.up.set(0, 0, 1);
      rendererRef.current = new THREE.WebGLRenderer({ antialias: true });
      rendererRef.current.setSize(200, 200);
    }

    const scene = sceneRef.current!;
    const camera = cameraRef.current!;
    const renderer = rendererRef.current!;

    if (!containerRef.current.firstChild) {
      containerRef.current.appendChild(renderer.domElement);
    }

    controlsRef.current = new OrbitControls(camera, renderer.domElement);
    const controls = controlsRef.current;

    controls.rotateSpeed = 0.2;
    controls.zoomSpeed = 1;

    const geometry = new THREE.BoxGeometry(1, 1, 1);
    const material = new THREE.MeshBasicMaterial({ color: 0xFFFFFF });
    const cube = new THREE.Mesh(geometry, material);
    const edges = new THREE.EdgesGeometry(geometry);
    const edgeMaterial = new THREE.LineBasicMaterial({ color: 0x000000 });
    const lines = new THREE.LineSegments(edges, edgeMaterial);
    cube.add(lines);  // Add lines to the cube,
    scene.add(cube);

    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };

    controls.addEventListener('change', () => {
      props.setRotation({
        source: props.controlId,
        rotation: camera.position.clone(),
      });
    });

    animate();

    return () => {
      renderer.dispose(); // Clean up on component unmount
    };
  }, []);

  useEffect(() => {
    if (!cameraRef.current || props.rotation?.source === props.controlId)
      return;
    const newRotation = props.rotation.rotation.clone();
    const scale = cameraRef.current.position.length() / props.rotation.rotation.length();

    newRotation.multiplyScalar(scale);

    cameraRef.current.position.copy(newRotation);

  }, [props.rotation, cameraRef.current]);

  return <div ref={containerRef} style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }} />;
});
