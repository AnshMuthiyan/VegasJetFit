import copy

import astropy.units as u
import numpy as np
from enum import Enum


def _row_band(row) -> str:
    """
    Return band/filter label from a CSV row.

    Supports both legacy ``Filter`` and newer ``Band`` column names.
    """
    band = getattr(row, 'Filter', None)
    if not isinstance(band, str):
        band = getattr(row, 'Band', None)

    if not isinstance(band, str):
        raise AttributeError("row has no valid 'Filter' or 'Band' column")

    band = band.strip()
    if not band:
        raise ValueError("row has empty band/filter label")
    return band


def q_e():
    """ The electron charge in cgs units. """
    return u.Quantity(4.8032e-10 * u.g**0.5 * u.cm**1.5 / u.s)


# <editor-fold desc="Enums">
class ScaleType(Enum):
    """
    Types of scales that can be applied to data values.

    Attributes
    ----------
    LINEAR : ScaleType
        Indicates a linear scale.

    LOG : ScaleType
        Indicates a base-10 logarithmic scale.

    LN : ScaleType
        Indicates a natural logarithmic (base-e) scale.

    Notes
    -----
    It is often useful to fit a model in one scale, but
    perform MCMC sampling in another scale. For example,
    a parameter space may cover many orders of magnitude
    which could make sampling very expensive and difficult.
    """
    LINEAR = 'linear'
    LOG    = 'log'
    LN     = 'ln'


class Prior(Enum):
    """

    """
    GAUSSIAN   = 'gaussian'
    TGAUSSIAN  = 'tgaussian'
    UNIFORM    = 'uniform'
    SINE       = 'sine'
    MILKYWAYRV = 'milkywayrv'


class DataType(Enum):
    """"""
    SPECTRAL_FLUX   = 'spectral flux'
    SPECTRAL_INDEX  = 'spectral index'
    INTEGRATED_FLUX = 'integrated flux'
# </editor-fold>


# <editor-fold desc="Mixins">
class BoundedMixin:
    """
    Adds tuple bounds with helper methods.

    Adds support for values that have an associated error region. Whether
    the bounds store (lower error, upper error), or (value + lower error,
    value + upper error) is up to the inheriting classes' implementation.

    Attributes
    ----------
    lower : float or astropy.units.Quantity
        The lower bound of the value.

    upper : float or astropy.units.Quantity
        The upper bound of the value.
    """
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def __repr__(self) -> str:
        return f"BoundedMixin(lower={self.lower}, upper={self.upper})"

    def bounds(self) -> tuple:
        """
        Returns the lower and upper bounds as a tuple.

        Returns
        -------
        tuple with length 2
            The lower and upper bound.
        """
        return self.lower, self.upper

    def encompasses(self, value):
        """
        Checks if the value is contained within the bounds.

        Parameters
        ----------
        value : float or astropy.units.Quantity
            The value to check.

        Returns
        -------
        bool
            True if value is contained within the bounds else False.
        """
        return self.lower <= value <= self.upper
# </editor-fold>


# <editor-fold desc="Data Structures">
class Bound:
    """
    A bounded region with units.

    Attributes
    ----------
    _lower : astropy.units.Quantity
        The lower bound.

    _upper : astropy.units.Quantity
        The upper bound.

    value : tuple
        The tuple of (`lower`, `upper`).
    """
    def __init__(self, lower, upper):
        self._lower = None
        self._upper = None
        self.value = (lower, upper)

    def __repr__(self) -> str:
        """ Returns a printable representation. """
        return f"Bound(lower={self.lower}, upper={self.upper})"

    @property
    def center(self) -> u.Quantity:
        """ Returns the center of the bounds. """
        return (self.lower + self.upper) / 2.0

    @property
    def width(self) -> u.Quantity:
        """ Returns the width of the bounds. """
        return self.upper - self.lower

    @property
    def value(self) -> tuple:
        """ Returns the lower and upper as a tuple. """
        return self._value

    @value.setter
    def value(self, value: tuple) -> None:
        """
        Sets `value` and updates `lower` and `upper`.

        Parameters
        ----------
        value : tuple of astropy.units.Quantity
            The new bounds.

        Raises
        ------
        UnitTypeError
            If units of `l` are not equivalent to the units
            of `upper`.

        ValueError
            If the lower bound is greater than the upper bound.
        """
        if len(value) != 2:
            raise ValueError('Bounds must be length two.')

        if value[0].unit.physical_type != value[1].unit.physical_type:
            raise u.UnitTypeError(
                f'Mismatch in units for lower and upper bounds: '
                f'{value[0].unit}, {value[1].unit}.'
            )

        self._value = value
        self._lower = value[0]
        self._upper = value[1]

    @property
    def lower(self) -> u.Quantity:
        """ Returns the lower bound. """
        return self.value[0]

    @lower.setter
    def lower(self, l: u.Quantity) -> None:
        """
        Sets the lower bound.

        Parameters
        ----------
        l : astropy.units.Quantity
            The new lower bound.
        """
        self.value = (l, self.upper)

    @property
    def upper(self) -> u.Quantity:
        """ Returns the upper bound. """
        return self.value[1]

    @upper.setter
    def upper(self, up: u.Quantity) -> None:
        """
        Sets the upper bound.

        Parameters
        ----------
        up : astropy.units.Quantity
            The new upper bound.
        """
        self.value = (self.lower, up)

    def encompasses(self, v, inclusive: bool = True) -> bool:
        """
        Checks if `v` is between `lower` and `upper`.

        If `v` is dimensionless, assumes that `v` has units
        equal to that of `lower` and `upper`.

        Parameters
        ----------
        v : float or astropy.units.Quantity
            The value to check.

        inclusive : bool, optional, default=True
            If `True`, does an inclusive check, else exclusive.

        Returns
        -------
        bool
            True if value is contained within the bounds else False.
        """
        v_quant = u.Quantity(v, self.lower.unit)

        if inclusive:
            return self._lower <= v_quant <= self._upper

        return self._lower < v_quant < self._upper


class FluxBase:
    """
    Flux Measurement Base. Not intended for direct use.

    Attributes
    ----------
    value : astropy.units.Quantity
        The flux value.

    time : astropy.units.Quantity
        The time of the flux measurement.

    uncertainty : tuple of astropy.units.Quantity, default=(None, None)
        The lower and upper bounds of the flux measurement.

    band : str, optional, default=None
        The name of the observed band. Useful for plotting.

    Parameters
    ----------
    lower : astropy.units.Quantity, optional
        The lower bound of the flux uncertainty.

    upper : astropy.units.Quantity, optional
        The upper bound of the flux uncertainty.
    """
    def __init__(
            self,
            value: u.Quantity,
            lower: u.Quantity,
            upper: u.Quantity,
            time: u.Quantity,
            band: str = None,
    ):
        self.value = value
        self.time = time
        self.uncertainty = Bound(lower, upper)
        self.band = band

    def copy(self):
        """ Returns a deepcopy of the object. """
        return copy.deepcopy(self)

    @property
    def avg_uncertainty(self) -> u.Quantity:
        """ Returns the avg of `lower` and `upper`. """
        return self.uncertainty.center

    @property
    def value(self) -> u.Quantity:
        """ Returns the flux value. """
        return self._value

    @value.setter
    def value(self, value: u.Quantity):
        """ Sets the flux value. """
        self._value = value

    @property
    def time(self) -> u.Quantity['time']:
        """
        Returns the time of the flux measurement.

        Returns
        -------
        astropy.units.Quantity['time']
            The time of the flux measurement.
        """
        return self._time

    @time.setter
    @u.quantity_input(t='time')
    def time(self, t: u.Quantity) -> None:
        """
        Sets the time of the flux measurement.

        Parameters
        ----------
        t : astropy.units.Quantity
            The time with units convertable to `time`.
        """
        self._time = t

    @property
    def uncertainty(self) -> Bound:
        """ Returns the bounds of the flux value. """
        return self._uncertainty

    @uncertainty.setter
    def uncertainty(self, b) -> None:
        """
        Sets the bounds of the flux value.

        Parameters
        ----------
        b : tuple of astropy.unit.Quantity or Bound
            The new bounds with units of `value`.
        """
        if isinstance(b, tuple):
            b = Bound(b[0], b[1])

        # Bound class already enforces units of lower, upper are equal
        # We only need to check if either is the same as value.
        if not (b.lower.unit.physical_type == self.value.unit.physical_type):
            raise u.UnitTypeError(
                f'Mismatch in units between bounds and value: '
                f'v={self.value.unit},l={b.lower.unit}, u={b.upper.unit}.'
            )

        self._uncertainty = b


class SpectralFlux(FluxBase):
    """
    Spectral flux density measurement.

    Parameters
    ----------
    value : astropy.units.Quantity
        The flux value.

    lower : astropy.units.Quantity
        The lower uncertainty.

    upper : astropy.units.Quantity
        The upper uncertainty.

    time : astropy.units.Quantity, optional
        The time of the flux measurement.

    frequency : astropy.units.Quantity
        The average band frequency with units of frequency.

    wavelength : astropy.units.Quantity
        The average band wavelength with units of length.

    Attributes
    ----------
    uncertainty : tuple of astropy.units.Quantity, default=(None, None)
        The lower and upper bounds of the flux measurement.
    """
    type = DataType.SPECTRAL_FLUX

    def __init__(
        self,
        value: u.Quantity,
        lower: u.Quantity,
        upper: u.Quantity,
        time: u.Quantity,
        frequency: u.Quantity = None,
        wavelength: u.Quantity = None,
        band: str = None,
    ):
        super().__init__(value, lower, upper, time, band)
        self._frequency = None
        self._wavelength = None

        if frequency is wavelength is None:
            raise ValueError(
                'Either frequency or wavelength must be '
                'specified.'
            )

        if frequency is not None:
            if wavelength is not None:
                raise ValueError(
                    'Frequency and wavelength may not be '
                    'specified simultaneously.'
                )
            self.frequency = frequency
        else:
            self.wavelength = wavelength

    def __repr__(self) -> str:
        """ Returns a printable representation. """
        return (
            f"SpectralFlux(value={self.value}, "
            f"time={self.time}, frequency={self.frequency})"
        )

    @classmethod
    def from_csv_row(cls, row):
        """
        Returns instance parsed from a row of a CSV row.

        row : NamedTuple
            `Value`: The value of the flux measurement,
            `ValueUnits`: The units `Value`,
            `ValueLower`: The lower uncertainty of `Value`,
            `ValueUpper`: The upper uncertainty of `Value`,
            `Time`: The time of the flux measurement,
            `TimeUnits`: The units of the time,
            `Wave`: The frequency or wavelength,
            `WaveUnits`: The units of `Wave`.

        Returns
        -------
        SpectralFlux
            Populated from the CSV row.

        Raises
        ------
        IOError
            Catches any error within the method and redirects
            into an IOError containing the row number.
        """
        try:
            params = {
                'value': u.Quantity(row.Value, row.ValueUnits),
                'lower': u.Quantity(row.ValueLower, row.ValueUnits),
                'upper': u.Quantity(row.ValueUpper, row.ValueUnits),
                'time': u.Quantity(row.Time, row.TimeUnits).to('d'),
                'band': _row_band(row)
            }

            wave = u.Quantity(row.Wave, row.WaveUnits)

            if wave.unit.physical_type == 'frequency':
                params['frequency'] = wave

            elif wave.unit.physical_type == 'length':
                params['wavelength'] = wave

            return cls(**params)

        except Exception as e:
            raise IOError(f'Row {row.Index} is invalid: {str(e)}')

    @property
    def value(self) -> u.Quantity['spectral flux density']:
        """
        Returns the spectral flux value.

        Returns
        -------
        astropy.units.Quantity['spectral flux density']
            The spectral flux value.
        """
        return super().value

    @value.setter
    @u.quantity_input(value='spectral flux density')
    def value(self, value: u.Quantity) -> None:
        """
        Sets the flux value.

        Parameters
        ----------
        value : astropy.units.Quantity['spectral flux density']
            The flux value.
        """
        self._value = value

    @property
    def frequency(self) -> u.Quantity:
        """
        Returns the frequency of the flux value.

        Returns
        -------
        astropy.units.Quantity['frequency']
            The frequency value.
        """
        return self._frequency

    @frequency.setter
    @u.quantity_input(frequency='frequency')
    def frequency(self, frequency: u.Quantity) -> None:
        """
        Sets the frequency.

        Parameters
        ----------
        frequency : astropy.units.Quantity['frequency']
            The band frequency.
        """
        self._frequency = frequency

        # Use units if exists, else default to mirco-meters
        w_unit = self.wavelength.unit \
            if self.wavelength is not None else u.um

        self._wavelength = frequency.to(
            unit=w_unit, equivalencies=u.spectral()
        )

    @property
    def wavelength(self) -> u.Quantity:
        """
        Returns the wavelength of the flux measurement.

        Returns
        -------
        astropy.units.Quantity
            The wavelength value.
        """
        return self._wavelength

    @wavelength.setter
    @u.quantity_input(wavelength='length')
    def wavelength(self, wavelength: u.Quantity) -> None:
        """
        Sets the wavelength.

        Updates the corresponding frequency attribute to be
        equivalent to the new wavelength. Reuses frequency
        units if defined, else defaults to Hertz.

        Parameters
        ----------
        wavelength : astropy.units.Quantity
            The band wavelength.
        """
        self._wavelength = wavelength

        # Use units if exists, else default to Hz
        f_unit = self.frequency.unit \
            if self.frequency is not None else u.Hz

        self._frequency = wavelength.to(
            unit=f_unit, equivalencies=u.spectral()
        )


class Integrable:
    """
    Integrable Mixin. Not meant for direct use.
    """
    _int_type = None

    def __init__(self, lower, upper):
        self.int_range = Bound(lower, upper)

    @property
    def int_type(self) -> str:
        """ Returns the physical type of the integration limits. """
        return self._int_type

    @property
    def int_range(self) -> Bound:
        """ Returns the integration range. """
        return self._int_range

    @int_range.setter
    def int_range(self, ir) -> None:
        """
        Sets the integration range.

        Parameters
        ----------
        ir : tuple of astropy.unit.Quantity or Bound
            The new bounds with units of `value`.
        """
        if isinstance(ir, tuple):
            ir = Bound(ir[0], ir[1])

        if ir.lower.unit != ir.upper.unit:
            raise u.UnitTypeError(
                f'Mismatch in units for lower and upper integration range.'
            )

        if ir.lower.unit.physical_type != self.int_type:
            raise u.UnitTypeError(
                f'`int_range` units must be equivalent to a {self.int_type}.'
            )

        self._int_range = ir


class IntegratedFlux(FluxBase, Integrable):
    """
    Integrated flux measurement.

    Parameters
    ----------
    value : astropy.units.Quantity
        The flux value.

    lower : astropy.units.Quantity
        The lower bound of the flux measurement.

    upper : astropy.units.Quantity
        The upper bound of the flux measurement.

    int_lower : astropy.units.Quantity
        The lower bound of the integration range.

    int_upper : astropy.units.Quantity
        The upper bound of the integration range.

    time : astropy.units.Quantity, optional
        The time of the flux measurement.

    Attributes
    ----------
    uncertainty : Bound
        The lower and upper bounds of the flux measurement.

    int_range : Bound
        The lower and upper bounds of the integration range.
    """
    type = DataType.INTEGRATED_FLUX
    _int_type = u.Hz.physical_type

    def __init__(
        self,
        value: u.Quantity,
        lower: u.Quantity,
        upper: u.Quantity,
        time: u.Quantity,
        int_lower: u.Quantity,
        int_upper: u.Quantity,
        band: str = None,
    ):
        FluxBase.__init__(self, value, lower, upper, time, band)
        Integrable.__init__(self, int_lower, int_upper)

    def __repr__(self) -> str:
        """ Returns a printable representation. """
        return (
            f"IntegratedFlux(value={self.value}, "
            f"time={self.time}, int_range={self.int_range})"
        )

    @classmethod
    def from_csv_row(cls, row):
        """
        Returns instance parsed from a row of a CSV row.

        row : NamedTuple
            `Value`: The value of the flux measurement,
            `ValueUnits`: Units of the flux measurement,
            `ValueLower`: The lower flux uncertainty,
            `ValueUpper`: The upper flux uncertainty,
            `Time`: The time of the flux measurement,
            `TimeUnits`: The units of the time,
            `WaveLower`: The lower integration bound,
            `WaveUpper`: The upper integration bound,
            `WaveUnits`: The units of the integrations bounds.

        Raises
        ------
        IOError
            Catches any error within the method and redirects
            into an IOError containing the row number.

        Returns
        -------
        IntegratedFlux
            Populated from the CSV row.
        """
        try:
            params = {
                'value': u.Quantity(row.Value, row.ValueUnits),
                'lower': u.Quantity(row.ValueLower, row.ValueUnits),
                'upper': u.Quantity(row.ValueUpper, row.ValueUnits),
                'time': u.Quantity(row.Time, row.TimeUnits).to('d'),
                'int_lower': u.Quantity(row.WaveLower, row.WaveUnits),
                'int_upper': u.Quantity(row.WaveUpper, row.WaveUnits),
                'band': _row_band(row),
            }
            return cls(**params)

        except Exception as e:
            raise IOError(f'Row {row.Index} is invalid: {str(e)}')

    @property
    def value(self) -> u.Quantity:
        """
        Returns the integrated flux value.

        Returns
        -------
        astropy.units.Quantity['energy flux']
            The integrated flux value.
        """
        return super().value

    @value.setter
    @u.quantity_input(value='energy flux')
    def value(self, value: u.Quantity) -> None:
        """
        Sets the flux value.

        Parameters
        ----------
        value : astropy.units.Quantity['energy flux']
            The flux value.
        """
        self._value = value

    @property
    def frequency(self) -> u.Quantity:
        """ Returns the log average of the integration limits. """
        log_avg = 0.5 * (
            np.log10(self.int_range.lower.value) +
            np.log10(self.int_range.upper.value)
        )
        return (10 ** log_avg) * self.int_range.lower.unit

    def to_spectral(self, unit: str | u.Unit = u.mJy) -> SpectralFlux:
        """
        Converts the integrated flux to a spectral flux density.

        Parameters
        ----------
        unit : str or astropy.units.Unit, optional, default=u.mJy
            The unit to return the spectral flux density. Must
            be a spectral flux density unit.

        Returns
        -------
        SpectralFlux
            The spectral flux [`unit`] equivalent.
        """
        return SpectralFlux(
            value=(self.value / self.int_range.width).to(unit),
            lower=(self.uncertainty.lower / self.int_range.width).to(unit),
            upper=(self.uncertainty.upper / self.int_range.width).to(unit),
            frequency=self.frequency,
            band=self.band,
            time=self.time
        )


class SpectralIndex(Integrable):
    """
    Spectral index measurement.

    Parameters
    ----------
    value : u.Quantity['dimensionless']
        The spectral index value.

    lower : u.Quantity['dimensionless']
        The lower uncertainty of the spectral index.

    upper : u.Quantity['dimensionless']
        The upper uncertainty of the spectral index.

    int_lower : astropy.units.Quantity
        The lower bound of the integration range.

    int_upper : astropy.units.Quantity
        The upper bound of the integration range.

    Attributes
    ----------
    int_range : Bound
        The lower and upper bounds of the integration range.
    """
    type = DataType.SPECTRAL_INDEX
    _int_type = u.Hz.physical_type  # type: ignore

    def __init__(
            self,
            value: u.Quantity,
            lower: u.Quantity,
            upper: u.Quantity,
            time: u.Quantity,
            int_lower: u.Quantity,
            int_upper: u.Quantity
    ):
        super().__init__(int_lower, int_upper)

        self.value = value
        self.time = time
        self.uncertainty = Bound(lower, upper)

    def __repr__(self) -> str:
        """ Returns a printable representation. """
        return (
            f"SpectralIndex(value={self.value}, "
            f"time={self.time}, int_range={self.int_range})"
        )

    @classmethod
    def from_csv_row(cls, row):
        """
        Returns instance parsed from a row of a CSV row.

        row : NamedTuple
            `Value`: The value of the index measurement,
            `ValueLower`: The lower index uncertainty,
            `ValueUpper`: The upper index uncertainty,
            `Time`: The effective time of the index measurement,
            `TimeUnits`: Units of the time,
            ...

        Raises
        ------
        IOError
            Catches any error within the method and redirects
            into an IOError containing the row number.

        Returns
        -------
        SpectralIndex
            Populated from the CSV row.
        """
        try:
            params = {
                'value': u.Quantity(row.Value),
                'lower': u.Quantity(row.ValueLower),
                'upper': u.Quantity(row.ValueUpper),
                'time': u.Quantity(row.Time, row.TimeUnits).to('d'),
                'int_lower': u.Quantity(row.WaveLower, row.WaveUnits),
                'int_upper': u.Quantity(row.WaveUpper, row.WaveUnits),
            }
            return cls(**params)

        except Exception as e:
            raise IOError(f'Row {row.Index} is invalid: {str(e)}') from e

    @property
    def avg_uncertainty(self) -> u.Quantity:
        """ Returns the avg of `lower` and `upper`. """
        return self.uncertainty.center
# </editor-fold>
