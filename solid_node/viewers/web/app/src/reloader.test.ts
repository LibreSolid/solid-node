/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// Stand-in for the browser WebSocket: exposes the on* handlers Reloader
// assigns so tests can fire them directly, without a live server.
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  url: string;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }
}

const latestSocket = () =>
  FakeWebSocket.instances[FakeWebSocket.instances.length - 1];

import { Reloader } from './reloader';

const BANNER_SELECTOR = '.reload-offline-banner';

beforeEach(() => {
  jest.useFakeTimers();
  FakeWebSocket.instances = [];
  (global as any).WebSocket = FakeWebSocket;
  document.body.innerHTML = '';
  (global as any).fetch = jest.fn(() =>
    Promise.resolve({
      json: () => Promise.resolve({}),
    }),
  );
});

afterEach(() => {
  jest.useRealTimers();
  jest.resetAllMocks();
});

describe('Reloader offline banner', () => {
  it('does not show a banner while the initial connection is still pending', () => {
    new Reloader(() => {}, () => {});

    expect(document.querySelector(BANNER_SELECTOR)).toBeNull();
  });

  it('does not flash a banner when the initial connection succeeds immediately', () => {
    new Reloader(() => {}, () => {});

    latestSocket().onopen?.();

    expect(document.querySelector(BANNER_SELECTOR)).toBeNull();
  });

  it('does not show the banner on the very first failed connection attempt (grace period)', () => {
    new Reloader(() => {}, () => {});

    latestSocket().onclose?.();

    expect(document.querySelector(BANNER_SELECTOR)).toBeNull();
  });

  it('shows the banner after a couple of failed initial-connect retries', () => {
    new Reloader(() => {}, () => {});

    // First failed attempt: still within grace, no banner yet.
    latestSocket().onclose?.();
    expect(document.querySelector(BANNER_SELECTOR)).toBeNull();

    // Retry fires ~2s later.
    jest.advanceTimersByTime(2000);
    expect(FakeWebSocket.instances).toHaveLength(2);

    // Second consecutive failure: grace exhausted, banner must appear.
    latestSocket().onclose?.();
    const banner = document.querySelector(BANNER_SELECTOR);
    expect(banner).not.toBeNull();
    expect(banner?.textContent).toMatch(/solid develop is not running/i);
  });

  it('shows the banner immediately once a previously-live connection drops', () => {
    new Reloader(() => {}, () => {});

    latestSocket().onopen?.();
    expect(document.querySelector(BANNER_SELECTOR)).toBeNull();

    latestSocket().onclose?.();

    const banner = document.querySelector(BANNER_SELECTOR);
    expect(banner).not.toBeNull();
    expect(banner?.textContent).toMatch(/model may be stale/i);
  });

  it('retries the dropped connection roughly every 2 seconds, indefinitely', () => {
    new Reloader(() => {}, () => {});

    latestSocket().onopen?.();
    latestSocket().onclose?.();
    expect(FakeWebSocket.instances).toHaveLength(1);

    jest.advanceTimersByTime(1999);
    expect(FakeWebSocket.instances).toHaveLength(1);

    jest.advanceTimersByTime(1);
    expect(FakeWebSocket.instances).toHaveLength(2);

    latestSocket().onclose?.();
    jest.advanceTimersByTime(2000);
    expect(FakeWebSocket.instances).toHaveLength(3);
  });

  it('on reconnect after a drop, triggers the full reload path and then clears the banner', async () => {
    const reload = jest.fn(() => Promise.resolve());
    new Reloader(() => {}, reload);

    latestSocket().onopen?.();
    latestSocket().onclose?.();
    expect(document.querySelector(BANNER_SELECTOR)).not.toBeNull();

    jest.advanceTimersByTime(2000);
    // Reconnect succeeds: same full-reload path a file-change "reload"
    // message would trigger (fetch /_build_error, then reload()).
    latestSocket().onopen?.();

    // Flush the microtask queue the async reconnect handler schedules.
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();

    expect(global.fetch).toHaveBeenCalledWith('/_build_error');
    expect(reload).toHaveBeenCalled();
    expect(document.querySelector(BANNER_SELECTOR)).toBeNull();
  });

  it('does not re-trigger the reload path on a first-ever successful connect', () => {
    const reload = jest.fn(() => Promise.resolve());
    new Reloader(() => {}, reload);

    latestSocket().onopen?.();

    expect(reload).not.toHaveBeenCalled();
  });
});
