/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// The published entry point deliberately keeps the auto-mount contract. Hosts
// that need an imperative viewer import viewer.ts instead, whose module load is
// side-effect free.

import { mount, ViewerOptions } from './viewer';
import { API_VERSION } from './version';

export { mount } from './viewer';
export { API_VERSION } from './version';
export const apiVersion = API_VERSION;

function autoMount(): void {
  const params = new URLSearchParams(window.location.search);
  const options: ViewerOptions = { animation: 'inline' };
  const time = Number(params.get('t'));
  if (params.has('t') && !Number.isNaN(time)) {
    options.time = time;
  }
  if (params.get('autoplay') === '0') {
    options.autoplay = false;
  }
  document.querySelectorAll<HTMLElement>('[data-solid-widget]').forEach(
    (element) => {
      const sourceUrl = element.dataset.solidWidget;
      if (!sourceUrl) {
        return;
      }
      mount(element, sourceUrl, options).catch((error) => {
        element.textContent = `solid-widget: ${error.message}`;
        console.error(error);
      });
    },
  );
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoMount);
  } else {
    autoMount();
  }
}
