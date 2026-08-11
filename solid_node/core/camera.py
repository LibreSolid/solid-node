# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Convert OpenSCAD command-line camera values into viewer vectors."""

from dataclasses import dataclass
from math import cos, radians, sin

OPENSCAD_FOV = 22.5


@dataclass(frozen=True)
class Camera:
    eye: tuple[float, float, float]
    target: tuple[float, float, float]
    up: tuple[float, float, float]
    fov: float = OPENSCAD_FOV


def parse_camera(specification):
    """Parse either OpenSCAD ``--camera`` form.

    Six values are the vector form (eye followed by target). Seven are the
    gimbal form (target translation, rotations, and distance).
    """
    pieces = specification.split(",")
    if len(pieces) not in (6, 7):
        raise ValueError(
            "camera requires either 6 numbers (eye,target) or 7 numbers "
            "(translation,rotation,distance)"
        )
    try:
        values = tuple(float(piece.strip()) for piece in pieces)
    except ValueError as error:
        raise ValueError("camera parameters must all be numbers") from error

    if len(values) == 6:
        return Camera(values[:3], values[3:], (0.0, 0.0, 1.0))

    target = values[:3]
    rx, ry, rz, distance = values[3:]
    # OpenSCAD's model view is LookAt((0,-d,0), origin, Z-up), followed
    # by Rx(90-rx), Ry(-ry), Rz(-rz), then translation by -target.
    # A Three.js camera needs the inverse transform in world coordinates.
    inverse = _multiply(
        _rotation_z(rz),
        _multiply(_rotation_y(ry), _rotation_x(rx - 90.0)),
    )
    offset = _apply(inverse, (0.0, -distance, 0.0))
    up = _apply(inverse, (0.0, 0.0, 1.0))
    eye = tuple(center + delta for center, delta in zip(target, offset))
    return Camera(eye, target, up)


def _rotation_x(degrees):
    angle = radians(degrees)
    return (
        (1.0, 0.0, 0.0),
        (0.0, cos(angle), -sin(angle)),
        (0.0, sin(angle), cos(angle)),
    )


def _rotation_y(degrees):
    angle = radians(degrees)
    return (
        (cos(angle), 0.0, sin(angle)),
        (0.0, 1.0, 0.0),
        (-sin(angle), 0.0, cos(angle)),
    )


def _rotation_z(degrees):
    angle = radians(degrees)
    return (
        (cos(angle), -sin(angle), 0.0),
        (sin(angle), cos(angle), 0.0),
        (0.0, 0.0, 1.0),
    )


def _multiply(left, right):
    return tuple(
        tuple(
            sum(left[row][index] * right[index][column] for index in range(3))
            for column in range(3)
        )
        for row in range(3)
    )


def _apply(matrix, vector):
    return tuple(
        sum(matrix[row][column] * vector[column] for column in range(3))
        for row in range(3)
    )
