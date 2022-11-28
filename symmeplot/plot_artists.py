from abc import ABC, abstractmethod
import numpy as np
import numpy.typing as npt
from mpl_toolkits.mplot3d.proj3d import proj_transform
from mpl_toolkits.mplot3d.art3d import PathPatch3D
from matplotlib.patches import FancyArrowPatch, Circle
from mpl_toolkits.mplot3d.art3d import Line3D as _Line3D
from typing import Sequence
from matplotlib import Path

__all__ = ['Line3D', 'Vector3D', 'Circle3D']


class ArtistBase(ABC):
    @abstractmethod
    def update_data(self, *args):
        pass


class Line3D(_Line3D, ArtistBase):
    def __init__(self, x: Sequence[float], y: Sequence[float],
                 z: Sequence[float], *args, **kwargs):
        super().__init__(np.array(x, dtype=np.float64),
                         np.array(y, dtype=np.float64),
                         np.array(z, dtype=np.float64), *args, **kwargs)

    def update_data(self, x: Sequence[float], y: Sequence[float],
                    z: Sequence[float]):
        self.set_data_3d(np.array(x, dtype=np.float64),
                         np.array(y, dtype=np.float64),
                         np.array(z, dtype=np.float64))


class Vector3D(FancyArrowPatch, ArtistBase):
    # Source: https://gist.github.com/WetHat/1d6cd0f7309535311a539b42cccca89c
    def __init__(self, origin: Sequence[float], vector: Sequence[float], *args,
                 **kwargs):
        super().__init__((0, 0), (0, 0), *args, **kwargs)
        self._origin = np.array(origin, dtype=np.float64)
        self._vector = np.array(vector, dtype=np.float64)

    def do_3d_projection(self, renderer=None):
        # https://github.com/matplotlib/matplotlib/issues/21688
        xs, ys, zs = proj_transform(
            *[(o, o + d) for o, d in zip(self._origin, self._vector)],
            self.axes.M)
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
        return min(zs)

    def update_data(self, origin: Sequence[float], vector: Sequence[float]):
        self._origin = np.array(origin, dtype=np.float64)
        self._vector = np.array(vector, dtype=np.float64)


class Circle3D(PathPatch3D, ArtistBase):
    """Patch to plot 3D circles
    Inpired by: https://stackoverflow.com/a/18228967/20185124
    """

    def __init__(self, center: Sequence[float], radius: float,
                 normal: Sequence[float] = (0, 0, 1), **kwargs):
        path_2d = self._get_2d_path(np.float64(radius))
        super().__init__(path_2d, **{'zs': 0} | kwargs)
        self._segment3d = self._get_segment3d(
            path_2d,
            np.array(center, dtype=np.float64),
            np.array(normal, dtype=np.float64))

    @staticmethod
    def _get_2d_path(radius: np.float64):
        circle_2d = Circle((0, 0), radius)
        path = circle_2d.get_path()  # Get the path and the associated transform
        trans = circle_2d.get_patch_transform()
        return trans.transform_path(path)  # Apply the transform

    @staticmethod
    def _get_segment3d(path_2d: Path, center: npt.NDArray[np.float64],
                       normal: npt.NDArray[np.float64]):
        normal /= np.linalg.norm(normal)
        verts = path_2d.vertices  # Get the vertices in 2D
        d = np.cross(normal, (0, 0, 1))  # Obtain the rotation vector
        M = Circle3D._rotation_matrix(d)  # Get the rotation matrix
        segment3d = np.array([np.dot(M, (x, y, 0)) for x, y in verts])
        for i, offset in enumerate(center):
            segment3d[:, i] += offset
        return segment3d

    @staticmethod
    def _rotation_matrix(d: np.array):
        """
        Calculates a rotation matrix given a vector d. The direction of d
        corresponds to the rotation axis. The length of d corresponds to
        the sin of the angle of rotation.
        """
        sin_angle = np.linalg.norm(d)
        if sin_angle == 0:
            return np.identity(3)
        d /= sin_angle
        eye = np.eye(3)
        ddt = np.outer(d, d)
        skew = np.array([[0, d[2], -d[1]],
                         [-d[2], 0, d[0]],
                         [d[1], -d[0], 0]], dtype=np.float64)
        M = ddt + np.sqrt(1 - sin_angle ** 2) * (eye - ddt) + sin_angle * skew
        return M

    def update_data(self, center: Sequence[float], radius: float,
                    normal: Sequence[float]):
        self._segment3d = self._get_segment3d(
            self._get_2d_path(np.float64(radius)),
            np.array(center, dtype=np.float64),
            np.array(normal, dtype=np.float64))
