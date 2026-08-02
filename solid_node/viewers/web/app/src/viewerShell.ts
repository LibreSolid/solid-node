/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

interface ViewerHandle {
  dispose(): void;
  reload(): Promise<void>;
}

interface ViewerBundle {
  mount(target: HTMLElement | string, source: string, options: {
    animation: 'inline';
    autoplay: true;
  }): Promise<ViewerHandle>;
}

declare global {
  interface Window {
    SolidNodeWidget?: ViewerBundle;
  }
}

interface ViewerStatus {
  available: boolean;
  apiVersion: number;
  remedy: string | null;
}

const BUNDLE_URL = '/_viewer/bundle.js';
const SNAPSHOT_URL = '/build/viewer.json';

export class ViewerShell {
  private handle: ViewerHandle | undefined;
  private disposed = false;

  constructor(private readonly target: HTMLElement) {}

  async start(): Promise<void> {
    const bundle = await this.loadBundle();
    if (this.disposed) {
      return;
    }
    const handle = await bundle.mount(this.target, SNAPSHOT_URL, {
      animation: 'inline', autoplay: true,
    });
    if (this.disposed) {
      handle.dispose();
      return;
    }
    this.handle = handle;
    document.title = await this.modelName();
  }

  async reload(): Promise<void> {
    await this.handle?.reload();
  }

  dispose(): void {
    this.disposed = true;
    this.handle?.dispose();
    this.handle = undefined;
  }

  private async loadBundle(): Promise<ViewerBundle> {
    const response = await fetch('/_viewer');
    const status = await response.json() as ViewerStatus;
    if (!status.available) {
      throw new Error(status.remedy || 'Viewer bundle is unavailable');
    }
    if (window.SolidNodeWidget) {
      return window.SolidNodeWidget;
    }
    await new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = BUNDLE_URL;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load viewer bundle'));
      document.head.appendChild(script);
    });
    if (!window.SolidNodeWidget) {
      throw new Error('Viewer bundle did not expose SolidNodeWidget');
    }
    return window.SolidNodeWidget;
  }

  private async modelName(): Promise<string> {
    const response = await fetch(SNAPSHOT_URL);
    const document = await response.json() as { root: { name: string } };
    return document.root.name.replace(/([A-Z])/g, ' $1').trim();
  }
}
