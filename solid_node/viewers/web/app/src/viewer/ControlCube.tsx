import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
//import { Rotation, getRotation } from './rotation';


type ControlCubeProps = {
//  rotation: {x: number; y: number; z: number};
  onRotate: (rotation: THREE.Vector3) => void;
};

const ControlCube: React.FC<ControlCubeProps> = ({ onRotate }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera>();
  const cubeRef = useRef<THREE.Mesh>();
  const positionRef = useRef<number[]>();

  useEffect(() => {
    if (!containerRef.current) return;

    const size = 1;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xe5e5e5);
    const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    camera.up.set(0, 0, 1);
    camera.position.z = size * 1.5;

    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(200, 200);
    if (!containerRef.current.firstChild) {
      containerRef.current.appendChild(renderer.domElement);
    }

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.addEventListener('change', () => {
      if (JSON.stringify(positionRef.current) !== JSON.stringify(camera.position))
        onRotate(camera.position.clone());
    });

    const geometry = new THREE.BoxGeometry(1, 1, 1);
    const material = new THREE.MeshBasicMaterial({ color: 0xFFFFFF });
    const cube = new THREE.Mesh(geometry, material);
    const edges = new THREE.EdgesGeometry(geometry);
    const edgeMaterial = new THREE.LineBasicMaterial({ color: 0x000000 });
    const lines = new THREE.LineSegments(edges, edgeMaterial);
    cube.add(lines);  // Add lines to the cube,
    scene.add(cube);
    cubeRef.current = cube;

    const animate = () => {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };

    animate();

  }, []);

  /*
  useEffect(() => {
    if (!cameraRef.current || !rotation)
      return;

    const oldRot = cameraRef.current.position;
    const newRot = rotation;
    const oldMod = (oldRot.x ** 2 + oldRot.y ** 2 + oldRot.z ** 2) ** 0.5;
    const newMod = (newRot.x ** 2 + newRot.y ** 2 + newRot.z ** 2) ** 0.5;
    const scale = oldMod / newMod;

    const pos = [
      newRot.x * scale,
      newRot.y * scale,
      newRot.z * scale,
    ];
    cameraRef.current?.position.set(pos[0], pos[1], pos[2]);
    positionRef.current = pos;

  }, [rotation, cameraRef.current]);
  */

  return <div ref={containerRef} style={{ width: '200px', height: '200px' }} />;
};

export default ControlCube;
