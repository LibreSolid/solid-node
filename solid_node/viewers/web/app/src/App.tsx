/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect, useRef, useState } from 'react';
import './App.css';
import { Reloader } from './reloader';
import { ViewerShell } from './viewerShell';

const App = () => {
  const host = useRef<HTMLDivElement>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!host.current) return;
    const shell = new ViewerShell(host.current);
    shell.start().catch((reason) => setError(String(reason)));
    new Reloader(setError, () => {
      shell.reload().catch((reason) => setError(String(reason)));
    });
    return () => shell.dispose();
  }, []);

  return (
    <div className="app">
      {error ? <pre className="build-error">{error}</pre> : <div ref={host} className="model" />}
    </div>
  );
};

export default App;
