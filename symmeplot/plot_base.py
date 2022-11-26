from abc import ABC, abstractmethod
from sympy.physics.vector import Vector, ReferenceFrame, Point
from matplotlib.pyplot import gca
from typing import Optional, Union, Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from mpl_toolkits.mplot3d import Axes3D
    from sympy import Expr
    from matplotlib.pyplot import Artist
    import numpy as np


__all__ = ['PlotBase']


class PlotBase(ABC):
    """Class with the basic attributes and methods for the plot objects."""

    def __init__(self, inertial_frame: ReferenceFrame, zero_point: Point,
                 origin: Optional[Union[Point, Vector]] = None,
                 name: Optional[str] = None):
        """Initialize a PlotBase instance.

        Parameters
        ==========
        inertial_frame : ReferenceFrame
            The reference frame with respect to which the object is oriented.
        zero_point : Point
            The absolute origin with respect to which the object is positioned.
        origin : Point, Vector, optional
            The origin of the object itself with respect to the zero_point. If a
            ``Vector`` is provided the ``origin`` will be at the tip of the
            vector with respect to the ``zero_point``. The default is the
            ``zero_point``.
        name : str, optional
            Name of the plot object. The default name is the name of the object
            that will be plotted.

        """
        self._children: List[PlotBase] = []
        self.inertial_frame = inertial_frame
        self.zero_point = zero_point
        self.origin = origin
        self.visible = True
        self.name = name
        self._values = []
        self._artists = []

    def __repr__(self):
        """Representation showing some basic information of the instance."""
        return (
            f"{self.__class__.__name__}(inertia_frame={self.inertial_frame}, "
            f"zero_point={self.zero_point}, origin={self.origin}, "
            f"name={self.name})")

    def __str__(self):
        return self.name

    @property
    def children(self) -> 'Tuple[PlotBase]':
        return tuple(self._children)

    @property
    def artists(self) -> 'List[Artist]':
        return self._artists + [
            artist for child in self._children for artist in child.artists]

    @property
    def name(self) -> str:
        """Returns the name of the plot object."""
        return self._name

    @name.setter
    def name(self, name: Optional[str]):
        self._name = str(name) if name is not None else name

    @property
    def inertial_frame(self) -> ReferenceFrame:
        """Returns the inertial frame of the object."""
        return self._inertial_frame

    @inertial_frame.setter
    def inertial_frame(self, new_inertial_frame: ReferenceFrame):
        if not isinstance(new_inertial_frame, ReferenceFrame):
            raise TypeError(
                "'inertial_frame' should be a valid ReferenceFrame object.")
        elif hasattr(self, '_inertial_frame'):
            raise NotImplementedError("'inertial_frame' cannot be changed.")
        else:
            for child in self._children:
                child.inertial_frame = new_inertial_frame
            self._inertial_frame = new_inertial_frame

    @property
    def zero_point(self) -> Point:
        """Returns the zero point of the object."""
        return self._zero_point

    @zero_point.setter
    def zero_point(self, new_zero_point: Point):
        if hasattr(self, '_zero_point') and new_zero_point != self._zero_point:
            raise NotImplementedError("'zero_point' cannot be changed")
        if not isinstance(new_zero_point, Point):
            raise TypeError("'zero_point' should be a valid Point object.")
        else:
            for child in self._children:
                child.zero_point = new_zero_point
            self._zero_point = new_zero_point

    @property
    def origin(self) -> Point:
        """Returns the origin of the object."""
        return self._origin

    @origin.setter
    def origin(self, new_origin: Optional[Union[Point, Vector]]):
        if new_origin is None:
            new_origin = self.zero_point
        elif isinstance(new_origin, Vector):
            new_origin = self.zero_point.locatenew('', new_origin)
        if isinstance(new_origin, Point):
            for child in self._children:
                child.origin = new_origin
            self._origin = new_origin
        else:
            raise TypeError("'origin' should be a valid Point object.")

    @property
    def visible(self) -> bool:
        """Returns if the object is visible in the plot."""
        return self._visible

    @visible.setter
    def visible(self, is_visible: bool):
        for child in self._children:
            child._visible = bool(is_visible)
        self._visible = bool(is_visible)

    @property
    def values(self) -> list:
        """Parameter values of the expressions required for plotting."""
        return [self._values] + [child.values for child in self._children]

    @values.setter
    def values(self, values: list):
        self._values = values[0]
        for child, vals in zip(self._children, values[1:]):
            child.values = vals

    @abstractmethod
    def _get_expressions_to_evaluate_self(self) -> 'List[Expr]':
        """Returns a list of the necessary expressions for plotting."""
        pass

    def get_expressions_to_evaluate(self) -> list:
        """Returns a list of the necessary expressions for plotting."""
        return [self._get_expressions_to_evaluate_self()] + [
            child.get_expressions_to_evaluate() for child in self._children]

    def evalf(self, *args, **kwargs) -> list:
        """Evaluates the expressions describing the object, using the ``evalf``
        function from sympy.

        Parameters
        ==========
        *args : Arguments that are passed to the SymPy evalf function.
        **kwargs : Kwargs that are passed to the SymPy evalf function.

        """
        expressions = self._get_expressions_to_evaluate_self()
        self._values = [expr.evalf(*args, **kwargs) for expr in expressions]
        for child in self._children:
            child.evalf(*args, **kwargs)
        return self.values

    @abstractmethod
    def _plot_self(self, ax: 'Axes3D') -> 'List[Artist]':
        pass

    def plot(self, ax: 'Optional[Axes3D]' = None) -> 'List[Artist]':
        """Adds the object artists to the matplotlib ``Axes``. Note that the
        object should be evaluated before plotting with for example the
        ``evalf`` method.

        Parameters
        ==========
        ax : matplotlib.axes._subplots.Axes3DSubplot, optional
            Axes on which the artist should be added. The default is the active
            axes.

        """
        if ax is None:
            ax = gca()
        artists = self._plot_self(ax)
        for child in self._children:
            artists += child.plot(ax)
        return artists

    @abstractmethod
    def _update_self(self) -> 'List[Artist]':
        pass

    def update(self) -> 'List[Artist]':
        """Updates the artists parameters, based on a current values."""
        artists = self._update_self()
        for child in self._children:
            artists += child.update()
        return artists

    @property
    @abstractmethod
    def annot_coords(self) -> 'np.array':
        pass

    def contains(self, event) -> bool:
        for artist in self.artists:
            if artist is not None and artist.contains(event)[0]:
                return True
        return False