# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import hashlib
import numpy as np

from solid_node.exact import (cached_shape, deflections, fuse_shapes,
                              placed_shape, write_brep, write_stl)
from solid_node.mesh_engine import require_mesh_engine
from .base import (_atomic_write_bytes, _compose_solid_matrix,
                   cached_base_mesh)
from .internal import InternalNode


class FusionNode(InternalNode):
    """
    Represents a fusion of components into a single, inseparable unit.
    This internal node can contain LeafNode or other FusionNode instances.
    The render method of this class returns a list of its child nodes.
    """

    _type = 'FusionNode'

    #: The tessellation precision of this fusion's OWN fused solid --
    #: see `ExactLeafNode.linear_deflection`/`angular_deflection` for the
    #: declaration shape, the currency and identity consequences, and the
    #: OCCT quantities these name. A fusion does NOT inherit either
    #: attribute from its children: the fuse is a different shape than
    #: any of them, and there is no defensible way to pick a winner among
    #: children that disagree.
    linear_deflection = 0.1
    angular_deflection = 0.1

    @property
    def geometry_recipe(self):
        if self.exact:
            return 'exact-fusion-occt-v1'
        ingredients = '\0'.join(child.geometry_recipe
                                 for child in self.children)
        return 'faceted-fusion-manifold-v1:' + hashlib.sha256(
            ingredients.encode()).hexdigest()

    def _artifact_recipe(self, path):
        if path == self.stl_file and self.children and not self.exact:
            return self.geometry_recipe
        return super()._artifact_recipe(path)

    @property
    def time(self):
        """You can't use self.time with a FusionNode, as the resulting object
        is expected to be rigid."""
        raise Exception(
            "FusionNode cannot rely on time; use AssemblyNode for animation")

    def validate(self, rendered):
        """A fusion combines solids into one solid, so every child must
        be rigid. You fuse first and assemble afterwards; an assembled
        thing has no single geometry to fuse.

        Checked here rather than in InternalNode so the base class does
        not have to know its own subclasses. Rigidity is determined by
        node type (ADR-003 as amended by ADR-039), so a child's `rigid`
        is already final at validation time -- nothing has to be
        rendered to ask the question.
        """
        super().validate(rendered)

        if not rendered:
            raise Exception(
                f'{self.name} must fuse at least one rigid child')

        for child in rendered:
            if not child.rigid:
                raise Exception(
                    f"{self.name} cannot fuse non-rigid child {child.name}; "
                    "fuse solids first, then assemble them")

    def shape(self):
        if not self.exact:
            return super().shape()
        if self._up_to_date(self.brep_file):
            return cached_shape(self.brep_file)
        placed = [
            placed_shape(child.shape(), _compose_solid_matrix(child))
            for child in self.children
        ]
        result = placed[0]
        for child, child_shape in zip(self.children[1:], placed[1:]):
            result = fuse_shapes(result, child_shape, self.name, child.name)
        return result

    def generate_stl(self):
        if not self.exact:
            return self._generate_faceted_stl()
        if (self._up_to_date(self.stl_file)
                and self._up_to_date(self.brep_file)):
            return
        shape = self.shape()
        digest = self.source_digest
        fingerprint = self.source_fingerprint
        write_brep(shape, self.brep_file, self.mtime_ns, digest, fingerprint)
        linear_deflection, angular_deflection = deflections(self)
        write_stl(shape, self.stl_file, self.mtime_ns,
                  linear_deflection, angular_deflection, digest, fingerprint)

    def _generate_faceted_stl(self):
        """Union current child artifacts in this fusion's local frame."""
        if self._up_to_date(self.stl_file):
            return
        Manifold, Mesh = require_mesh_engine(
            f"faceted fusion {self.name}",
            "directly unioning its children's mesh artifacts")

        manifolds = []
        for child in self.children:
            mesh = cached_base_mesh(child.stl_file).copy()
            mesh.apply_transform(_compose_solid_matrix(child))
            manifold = Manifold(mesh=Mesh(
                vert_properties=np.asarray(mesh.vertices, np.float32),
                tri_verts=np.asarray(mesh.faces, np.uint32),
            ))
            status = manifold.status()
            if str(status).split('.')[-1] != 'NoError':
                raise ValueError(
                    f"faceted fusion {self.name} cannot admit child "
                    f"{child.name}: manifold3d reported {status}")
            manifolds.append(manifold)

        result = manifolds[0]
        for manifold in manifolds[1:]:
            result = result + manifold
        status = result.status()
        if str(status).split('.')[-1] != 'NoError':
            raise ValueError(
                f"faceted fusion {self.name} failed: manifold3d reported "
                f"{status}")

        output = result.to_mesh()
        trimesh = __import__('trimesh')
        fused = trimesh.Trimesh(
            vertices=np.asarray(output.vert_properties[:, :3], np.float64),
            faces=np.asarray(output.tri_verts, np.int64), process=False,
        )
        _atomic_write_bytes(
            self.stl_file, fused.export(file_type='stl'), self.mtime_ns,
            self.source_digest, self.source_fingerprint,
            self._artifact_recipe(self.stl_file),
        )
