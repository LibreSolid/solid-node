/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

type SetTimeFunction = (time: number | ((prevTime: number) => number)) => void

export class Animator {
  private static instance: Animator | null = null;
  private setTime: SetTimeFunction;
  private fps: number = 0;
  private frames: number = 0;
  private timeIncrement: number = 0;
  private framePeriod: number = 0;
  private lastFrameTime: number;
  private currentTime: number = 0;

  private constructor(setTime: SetTimeFunction) {
    this.setTime = setTime;
    this.lastFrameTime = 0;

    this.animate = this.animate.bind(this);
    this.animate(0);
  }

  public static getInstance(setTime: SetTimeFunction): Animator {
    if (!Animator.instance) {
      Animator.instance = new Animator(setTime);
    }
    return Animator.instance;
  }

  public setAnimation(fps: number, frames: number): void {
    this.fps = fps;
    this.frames = frames;
    this.timeIncrement = 1 / frames;
    this.framePeriod = 1000 / fps;
  }

  private animate(timestamp: number) {
    if (this.fps > 0 && this.frames > 0) {
      const elapsed = timestamp - this.lastFrameTime;

      if (elapsed > this.framePeriod) {
        this.setTime((time) => (time + this.timeIncrement) % 1);
        this.lastFrameTime = timestamp;
      }
    }

    requestAnimationFrame(this.animate);
  }
}
