
.. _status-and-roadmap:

==========================
Project status and roadmap
==========================

This project has been developed and maintained by a single person so far, and as it is, it's pretty usable. It can already solve real bottlenecks in mechanical project development. It's still a bit far from 1.0 version, but the **current node API should not change** until there, so you're invited to use it in your next 3D printable Open Source project.

Version 0.4 added ``solid export`` and the embedding pipeline — models
render in any static web page or Sphinx documentation, animations
included (see :doc:`embedding`) — along with a more robust builder
that recovers from broken edits.

Roadmap
=======

  * A command to pack the project into a distributable with source and builds
  * Improve the web viewer with workplanes, rulers, camera angles, animation scrubbing, a test runner
  * A FlexibleNode class to create objects that change shape over time, with keyframes for animation
