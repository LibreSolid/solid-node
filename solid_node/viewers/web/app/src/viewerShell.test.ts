/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import { ViewerShell } from './viewerShell';

const mount = jest.fn();
const reload = jest.fn();
const dispose = jest.fn();

beforeEach(() => {
  document.head.innerHTML = '';
  document.title = '';
  mount.mockReset().mockResolvedValue({ reload, dispose });
  reload.mockReset().mockResolvedValue(undefined);
  dispose.mockReset();
  delete window.SolidNodeWidget;
  (global as any).fetch = jest.fn((url: string) => {
    if (url === '/_viewer') {
      return Promise.resolve({ json: () => Promise.resolve({
        available: true, apiVersion: 1, remedy: null,
      }) });
    }
    return Promise.resolve({ json: () => Promise.resolve({
      root: { name: 'SpinnerProject' },
    }) });
  });
});

afterEach(() => jest.resetAllMocks());

it('loads the shared bundle, mounts it, and delegates reload/dispose', async () => {
  const host = document.createElement('div');
  const shell = new ViewerShell(host);
  const starting = shell.start();
  await new Promise((resolve) => setTimeout(resolve, 0));
  const script = document.head.querySelector('script');
  expect(script?.src).toContain('/_viewer/bundle.js');
  window.SolidNodeWidget = { mount };
  script?.dispatchEvent(new Event('load'));
  await starting;

  expect(mount).toHaveBeenCalledWith(host, '/build/viewer.json', {
    animation: 'inline', autoplay: true,
  });
  expect(document.title).toBe('Spinner Project');

  await shell.reload();
  shell.dispose();
  expect(reload).toHaveBeenCalledTimes(1);
  expect(dispose).toHaveBeenCalledTimes(1);
});

it('reports the backend remedy instead of loading a missing bundle', async () => {
  (global as any).fetch = jest.fn(() => Promise.resolve({
    json: () => Promise.resolve({
      available: false, apiVersion: 1, remedy: 'run npm run build',
    }),
  }));

  await expect(new ViewerShell(document.createElement('div')).start())
    .rejects.toThrow('run npm run build');
  expect(mount).not.toHaveBeenCalled();
});

it('disposes a viewer that resolves after its shell was cleaned up', async () => {
  let resolveMount: (handle: { reload: typeof reload; dispose: typeof dispose }) => void;
  mount.mockImplementation(() => new Promise((resolve) => {
    resolveMount = resolve;
  }));
  window.SolidNodeWidget = { mount };
  const shell = new ViewerShell(document.createElement('div'));

  const starting = shell.start();
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(mount).toHaveBeenCalledTimes(1);

  shell.dispose();
  resolveMount!({ reload, dispose });
  await starting;

  expect(dispose).toHaveBeenCalledTimes(1);
});

it('does not mount when cleanup finishes before the bundle is ready', async () => {
  let resolveStatus: (status: {
    available: boolean; apiVersion: number; remedy: null;
  }) => void;
  (global as any).fetch = jest.fn(() => Promise.resolve({
    json: () => new Promise((resolve) => { resolveStatus = resolve; }),
  }));
  window.SolidNodeWidget = { mount };
  const shell = new ViewerShell(document.createElement('div'));

  const starting = shell.start();
  await Promise.resolve();
  await Promise.resolve();
  shell.dispose();
  resolveStatus!({ available: true, apiVersion: 1, remedy: null });
  await starting;

  expect(mount).not.toHaveBeenCalled();
});
