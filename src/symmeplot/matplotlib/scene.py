from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d.proj3d import proj_transform
from sympy.physics.vector import ReferenceFrame

from symmeplot.core import SceneBase
from symmeplot.matplotlib.plot_base import MplPlotBase
from symmeplot.matplotlib.plot_objects import (
    PlotBody,
    PlotFrame,
    PlotLine,
    PlotPoint,
    PlotVector,
)

__all__ = ["Scene3D"]

class Scene3D(SceneBase):
    """Class for plotting sympy mechanics in matplotlib.

    Parameters
    ----------
    inertial_frame : ReferenceFrame
        The reference frame with respect to which all objects will be oriented.
    origin : Point
        The absolute origin with respect to which all objects will be positioned.
    ax : mpl_toolkits.mplot3d.axes3d.Axes3D, optional
        Axes on which the sympy mechanics should be plotted.
    **inertial_frame_properties : dict, optional
        Keyword arguments are parsed to the
        :class:`symmeplot.matplotlib.plot_objects.PlotFrame` representing the inertial
        reference frame.

    Examples
    --------
    .. jupyter-execute::

        import matplotlib.pyplot as plt
        import sympy.physics.mechanics as me
        from symmeplot.matplotlib import Scene3D

        N = me.ReferenceFrame("N")
        A = me.ReferenceFrame("A")
        A.orient_axis(N, N.z, 1)
        N0 = me.Point("N_0")
        v = 0.2 * N.x + 0.2 * N.y + 0.7 * N.z
        A0 = N0.locatenew("A_0", v)
        scene = Scene3D(N, N0, scale=0.5)
        scene.add_vector(v, name="v")
        scene.add_frame(A, A0, ls="--")
        scene.lambdify_system(())
        scene.evaluate_system()
        scene.plot()

    """

    _PlotPoint: type[MplPlotBase] = PlotPoint
    _PlotLine: type[MplPlotBase] = PlotLine
    _PlotVector: type[MplPlotBase] = PlotVector
    _PlotFrame: type[MplPlotBase] = PlotFrame
    _PlotBody: type[MplPlotBase] = PlotBody

    def __init__(self, inertial_frame, zero_point, ax=None, **inertial_frame_properties
                 ):
        if ax is None:
            fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
        if not hasattr(ax, "get_zlim"):
            raise TypeError("The axes should be a 3d axes")
        super().__init__(inertial_frame, zero_point, **inertial_frame_properties)
        self._ax = ax
        self.annot = self._ax.text2D(
            0, 0, "", bbox={"boxstyle": "round4", "fc": "linen", "ec": "k", "lw": 1},
            transform=None)
        self.annot.set_visible(False)
        self.annot_location = "object"
        self._ax.figure.canvas.mpl_connect("motion_notify_event", self._hover)

    @property
    def axes(self):
        """Axes used by the scene."""
        return self._ax

    @property
    def annot_location(self):
        """String describing where the annotation should be displayed.

        Explanation
        -----------
        String that is used to determine where the annotation should be displayed.
        Options are:
        - `'object'`: The annotation location is determined based on the `plot_object`
        """
        return self._annot_location

    @annot_location.setter
    def annot_location(self, new_annot_location):
        if new_annot_location == "object":
            self._annot_location = new_annot_location
        else:
            raise NotImplementedError(
                f"Annotation location '{new_annot_location}' has not been "
                f"implemented.")

    @property
    def annot_coords(self):
        """Coordinate where the annotation text is displayed."""
        return self.annot.get_position()

    def plot(self, prettify=True, ax_scale=1.5):
        """Plot all plot objects.

        Parameters
        ----------
        prettify : bool, optional
            If True prettify the axes. Default is True.
        ax_scale : float, optional
            Makes the axes bigger in the figure. This function is part of prettifying
            the figure and only works nicely if it is the only subplot. Disabled if set
            to 0. Default is 1.5

        Returns
        -------
        tuple of artists
            Returns the plotted artists

        """
        self.update()
        for plot_object in self._children:
            plot_object.plot(self.axes)
        if prettify:
            self.axes.autoscale_view()
            for axis in (self.axes.xaxis, self.axes.yaxis, self.axes.zaxis):
                axis.set_ticklabels([])
                axis.set_ticks_position("none")
            if ax_scale:
                self.axes.set_position(
                    [-(ax_scale - 1) / 2, -(ax_scale - 1) / 2, ax_scale, ax_scale])
            self.auto_zoom()
            self.axes.set_aspect("equal", adjustable="box")

    def set_plot_as_2d(self, frame: ReferenceFrame | None = None) -> None:
        """Change the axis to an orhogonal projection making the view seemingly 2D.

       Parameters
       ----------
       frame: ReferenceFrame, optional
           Reference frame w.r.t. which the axis view is oriented aligning the users view
           with the XY plane. The default is the inertial frame of the scene.

        """
        projection_frame = ReferenceFrame("A")
        projection_frame.orient_axis(self.inertial_frame, self.inertial_frame.z, 0)
        frame = frame or projection_frame
        self.axes.set_proj_type("ortho")
        self.axes.view_init(**self.get_euler_angels(self.inertial_frame, frame))

    @staticmethod
    def get_euler_angels(normal_frame: ReferenceFrame, projection_frame: ReferenceFrame,
                         ) -> dict[str, float]:
        """Get the Euler angles of the given frame.

        Parameters
        ----------
        normal_frame : ReferenceFrame
            Reference frame for which the Euler angles should be calculated.
        projection_frame : ReferenceFrame
            Reference frame for which the Euler angles should be calculated.

        Returns
        -------
        tuple of float
            The Euler angles in the order of (elev, azim, roll).

        """
        direction_matrix = np.array(projection_frame.dcm(normal_frame)).astype(np.float64)
        azimuth = np.arctan2(direction_matrix[1, 0], direction_matrix[0, 0])
        elevation = np.arcsin(-direction_matrix[2, 0])
        roll = np.arctan2(direction_matrix[2, 1], direction_matrix[2, 2])
        return {
            "elev": np.rad2deg(elevation),
            "azim": np.rad2deg(azimuth),
            "roll": np.rad2deg(roll),
        }

    def auto_zoom(self, scale=1.1):
        """Auto scale the axis."""
        _artists = self.artists
        if not _artists:
            return
        _min = np.min([artist.min() for artist in _artists], axis=0)
        _max = np.max([artist.max() for artist in _artists], axis=0)
        size = scale * np.max(_max - _min)
        extra = (size - (_max - _min)) / 2
        self.axes.set_xlim(_min[0] - extra[0], _max[0] + extra[0])
        self.axes.set_ylim(_min[1] - extra[1], _max[1] + extra[1])
        self.axes.set_zlim(_min[2] - extra[2], _max[2] + extra[2])
        return _min, _max

    def _get_selected_object(self, event):
        """Get the `plot_object` where the mouseevent is currently on."""
        for plot_object in self._children:
            if plot_object.contains(event):
                return plot_object

    def _update_annot(self, plot_object, event):
        """Update the annotation to the given `plot_object`."""
        self.annot.set_text(str(plot_object))
        if self.annot_location == "object":
            x, y, _ = proj_transform(*plot_object.annot_coords,
                                     self._ax.get_proj())
            self.annot.set_position(self._ax.transData.transform((x, y)))
            # self.annot.set_position_3d(plot_object.annot_coords)
        elif self.annot_location == "mouse":
            self.annot.set_position(self._ax.transData.transform(
                (event.xdata, event.ydata)))

    def _hover(self, event):
        """Show an annotation if the mouse is hovering over a `plot_object`."""
        if event.inaxes == self._ax:
            plot_object = self._get_selected_object(event)
            if plot_object is not None:
                self._update_annot(plot_object, event)
                self.annot.set_visible(True)
                self._ax.figure.canvas.draw_idle()
            elif self.annot.get_visible():
                self.annot.set_visible(False)
                self._ax.figure.canvas.draw_idle()

    def clear(self):
        """Clear the axes.

        Explanation
        -----------
        Remove all artists known by the instance. Only the inertial frame as plotobject
        in the scene.
        """
        for plot_object in self._children:
            plot_object.set_visible(False)
        self._children = [self._children[0]]

    def animate(self, get_args: Callable[[Any], tuple], frames: Iterable[Any] | int,
                interval: int = 30, **kwargs) -> FuncAnimation:
        """Animate the scene.

        Parameters
        ----------
        get_args : Callable
            Function that returns the arguments for the ``evaluate_system`` method. The
            function should takes the current frame as input.
        frames : int or iterable
            Number of frames or iterable with frames.
        interval : int, optional
            Time interval between frames in milliseconds. Default is 30.
        **kwargs
            Keyword arguments are parsed to the
            :class:`matplotlib.animation.FuncAnimation`.

        Returns
        -------
        matplotlib.animation.FuncAnimation
            Animation object.

        """

        def update(frame):
            self.evaluate_system(*get_args(frame))
            self.update()
            return self.artists

        if isinstance(frames, int):
            frames = range(frames)
        return FuncAnimation(self.axes.figure, update, frames=frames, interval=interval,
                             **{"blit": True, **kwargs})
