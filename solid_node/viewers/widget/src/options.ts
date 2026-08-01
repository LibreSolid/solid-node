/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import type { ViewerOptions, AnimationMode } from './viewer';

export interface ResolvedViewerOptions {
  baseUrl: string | null;
  animation: AnimationMode;
  time: number;
  autoplay: boolean;
  view: NonNullable<ViewerOptions['view']> | null;
  className: string | null;
  role: string | null;
  ariaLabel: string | null;
}

export interface ControlPlan {
  bar: boolean;
  toggle: boolean;
  collapsed: boolean;
  styled: boolean;
  hostDriven: boolean;
}

export function resolveOptions(
  options: ViewerOptions = {},
): ResolvedViewerOptions {
  const time = Number.isFinite(options.time) ? options.time! : 0;
  return {
    baseUrl: options.baseUrl ?? null,
    animation: options.animation ?? 'inline',
    time: Math.min(Math.max(time, 0), 1),
    autoplay: options.autoplay ?? true,
    view: options.view ?? null,
    className: options.className ?? null,
    role: options.role ?? null,
    ariaLabel: options.ariaLabel ?? null,
  };
}

export function resolveBaseUrl(sourceUrl: string, baseUrl?: string): string {
  const root = baseUrl ?? sourceUrl.replace(/[?#].*$/, '').replace(/[^/]*$/, '');
  return root.endsWith('/') ? root : `${root}/`;
}

export function controlPlan(
  mode: AnimationMode,
  animated: boolean,
): ControlPlan {
  if (!animated) {
    return { bar: false, toggle: false, collapsed: false, styled: false,
      hostDriven: mode === 'external' };
  }

  switch (mode) {
    case 'toggle':
      return { bar: true, toggle: true, collapsed: true, styled: false,
        hostDriven: false };
    case 'none':
      return { bar: false, toggle: false, collapsed: false, styled: false,
        hostDriven: false };
    case 'external':
      return { bar: false, toggle: false, collapsed: false, styled: false,
        hostDriven: true };
    case 'inline':
      return { bar: true, toggle: false, collapsed: false, styled: true,
        hostDriven: false };
  }
}
