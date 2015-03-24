# Copyright (C) 2015 Nathan Charles
#
# This program is free software. See terms in LICENSE file.
"""Typical Loads.

This Module contains various example loads.

"""
import environment as env
import csv
import datetime
import numpy as np
import random
from scipy.interpolate import interp1d
from devices import Device
from econ import Bid
from misc import Counter

SMALL_ID = Counter()

NEW_YEAR = datetime.datetime(2013, 1, 1)
hour_to_dt = lambda x: NEW_YEAR + datetime.timedelta(hours=x)

FMT = '%Y-%m-%d %H:%M:%S'

LOAD_PROFILE = [0.645, 0.615, 0.585, 0.569, 0.552, 0.541, 0.53, 0.525, 0.521,
                0.527, 0.534, 0.557, 0.581, 0.599, 0.617, 0.666, 0.715, 0.744,
                0.774, 0.768, 0.762, 0.754, 0.746, 0.747, 0.747, 0.743, 0.739,
                0.72, 0.7, 0.711, 0.722, 0.725, 0.728, 0.759, 0.79, 0.893,
                0.997, 1.0, 0.995, 0.987, 0.977, 0.937, 0.896, 0.857, 0.817,
                0.757, 0.696, 0.667, 0.638]


def simple_profile(dt, mult=1.):
    offset = int(round(dt.hour*2.0))
    return LOAD_PROFILE[offset] * mult


def _load(filename=None):
    BD = {}
    if filename is None:
        filename = env.SRC_PATH + '/bd_hist_profile.csv'
    foo = csv.reader(open(filename))
    for i in foo:
        lp = [float(j.strip()) for j in i[2:50]]
        tdt = datetime.datetime.strptime(i[0][0:19], FMT).date()
        # , len(lp),lp
        BD[tdt] = lp
    return BD


class Load(Device):
    """Load primative object.

    This is the base object that all loads inherit.
    """
    def bid(self):
        """Returns: (object): bid for energy"""
        e = self.needsenergy()
        if e:
            return Bid(id(self), e, self.buy_kwh())
        else:
            return None

    def needsenergy(self):
        """Returns: (float): energy need"""
        key = env.time
        if key not in self.balance:
            dmnd = self.demand(key)
            self.balance[key] = dmnd
            self.dmnd[key] = dmnd
        return self.balance[key]

    def power_io(self, energy):
        """Energy transfer.

        Args:
            energy (float): in wH.

        Returns: i
            (float): energy still needed.
        """
        key = env.time
        self.balance[key] += energy
        return self.balance[key]

    def buy_kwh(self):
        """Returns: (float) value of kwh."""
        return self.value_kwh()

    def enabled(self):
        """Returns: (float) total energy load has actually used."""
        td = self.total() * env.total_time/self.interval
        sf = sum(self.balance.values())
        return abs(td - sf)

    def value_kwh(self):
        return self.per_kwh

    def droopable(self):
        """Returns: (float) droopable ratio of desired energy."""
        return self.droop_ratio


class Annual(Load):

    """Annual Weather Data Nominilized to 1 kWH annual.

    This is class is based on typical Bangladesh grid loads. The data was mined
    from Bangladesh Power Development Boards daily reporting. It is nominilized
    to 1 kWh annual load and can be scaled using a multiplier to have a desired
    total load.

    Attributes:
        mult (float): scaling factor
        year (int): year
    """

    def __init__(self, mult=71.4, year=2013):
        """Initialize.

        Args:
            mult (float): scaling factor (default 71.4)
            year (int): (default 2013)

        """
        self.mult = mult
        self.classification = "load"
        self.deferable = False
        self.droop_ratio = 0.
        self.year = year
        self.per_kwh = 0.07
        self.data = _load()
        self.small_id = SMALL_ID.next(type(self))
        self.balance = {}
        self.dmnd = {}
        self.detail = None
        self.interval = 365*24.

    def demand(self, dt):
        """ Demand at time.

        >>> BD = Annual(100.)
        >>> round(BD(datetime.datetime(2014, 12, 16, 20)),1)
        -11.7

        >>> round(BD(datetime.datetime(2014, 1, 16, 3)), 1)
        -7.2

        Args:
            dt (datetime)

        Returns:
            (float) Wh

        """
        mdt = datetime.date(self.year, dt.month, dt.day)
        offset = int(round(dt.hour*2.0))
        return -self.data[mdt][offset]*self.mult/40812.5

    __call__ = demand

    def total(self):
        """Total load for year.

        >>> BD = Annual(100.)
        >>> round(BD.total(), 1)
        -100000.0


        Returns:
            (float) Wh

        """
        return sum(self(hour_to_dt(i)) for i in range(365*24))

    def __repr__(self):
        if not self.detail:
            self.detail = '%s kWh Annual' % round(self.total()/1000., 1)
        return self.detail


class FanLoad(Load):

    """Fan Load.

    Atributes:
        wattage (float): in negative wH.
        thermostat (float): setting fan turns on in (C).
        per_kwh (float): value of kWh.
    """

    def __init__(self, wattage, thermostat=28.):
        """Initialize.

        Args:
            wattage (float): W
            thermostat (float): W
        """
        self.wattage = -wattage
        self.thermostat = thermostat
        self.per_kwh = 0.075
        self.droop_ratio = 0.
        self.dmnd = {}
        self.balance = {}
        self.interval = 24*265.

    def demand(self, key):
        """Demand returns (float) wH energy demand for (key)."""
        if key not in self.dmnd:
            if float(env.weather[key]["Dry-bulb (C)"]) > self.thermostat:
                self.dmnd[key] = self.wattage
            else:
                self.dmnd[key] = 0.

        return self.dmnd[key]

    def total(self):
        return sum(self.dmnd.values())

    __call__ = demand

    def __repr__(self):
        return '%s W Fan' % self.wattage


class LightingLoad(Load):

    """Lighting Load.

    Atributes:
        wattage (float): in negative wH.
        lux (float): setting lux
        hour (float): do not turn on before this hour.
        per_kwh (float): value of kWh.
    """

    def __init__(self, wattage, lux=400., hour=12.):
        """Initialize.

        Args:
            wattage (float): W
            thermostat (float): W
        """
        self.wattage = - abs(wattage) # ensure negative
        self.lux = lux
        self.per_kwh = 0.075
        self.dmnd = {}
        self.droop_ratio = 0.
        self.hour = hour
        self.balance = {}
        self.interval = 24*265.

    def demand(self, key):
        """Demand returns (float) wH energy demand for (key)."""
        if key not in self.dmnd:
            if float(env.weather[key]["DFIL (lux)"]) < self.lux and \
                    env.time.hour > self.hour:
                self.dmnd[key] = self.wattage
            else:
                self.dmnd[key] = 0.

        return self.dmnd[key]

    def total(self):
        return sum(self.dmnd.values())

    __call__ = demand

    def __repr__(self):
        return '%s W Lighting Load' % self.wattage


class DailyLoad(Load):

    """Spline interpolated Load Profile.

    Attributes:
        per_kwh (float): value of energy.
    """

    def __init__(self, hours, loads, kind='cubic', name=''):
        """Initilize.

        len(hours) == len(loads)

        Args:
            hours (list): of times (float) in hours.
            loads (list): of total loads at hour (float) wH.
            kind  (str): interpolation method default (cubic).
            name (str):
        """
        self.profile = interp1d(hours, loads, kind=kind)
        self.name = name
        self.classification = "load"
        self.deferable = False
        self.droop_ratio = 0.
        self.per_kwh = 0.07
        self.small_id = SMALL_ID.next(name)
        self.balance = {}
        self.dmnd = {}
        self.interval = 24.

    def demand(self, dt):
        """Return (float) energy demand wH for (datetime)."""
        return self.profile(dt.hour + dt.minute/60.)

    def total(self):
        return sum([self(hour_to_dt(i)) for i in range(24)])

    __call__ = demand

    def __repr__(self):
        return "%s %s, %s wH Daily" % (self.name, self.small_id,
                                       round(self.total(), 1))

times = np.array(range(0, 49))/2.
spline_profile = DailyLoad(times, np.array(LOAD_PROFILE)*17)


def tv(wattage=20):
    """TV load.

    Args:
        wattage (float): base load

    Returns:
        (object) : DailyLoad object with TV profile
    """
    # todo: do i really want this as a function?

    l = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                  -1, -1, -1, -1, 0, 0])
    h = range(25)  # to get 24 hour interpolation
    tv_inst = DailyLoad(h, l*wattage, kind='linear', name='12" B&W TV')
    tv_inst.per_kwh = .09
    return tv_inst

TV = tv(20)

FLAT = DailyLoad([0, 25], [8.15, 8.15], kind='linear', name='Flat')

# Average Load Profile from 2013 Annual
BD_AVE = [0.]*24
BD = Annual()
for i in range(24*365):
    dt = hour_to_dt(i)
    BD_AVE[dt.hour] += BD(dt)

BD_AVE.append(BD_AVE[0])  # End of day is the same as beginning
BD_AVE = DailyLoad(range(len(BD_AVE)), np.array(BD_AVE)/365.,
                   name='Mean Daily')


def noisy_profile(t):
    # +/1 10%
    return spline_profile(t)*(.9+random.random()/5.)


def quantify_load(load, solar_gen):
    """How much of a load can be met by sunlight?

    """
    l = np.array(load)
    g = np.array(solar_gen)

    d = g - l
    met_hours = sum(d >= 0)
    unmet_hours = sum(d < 0)
    return met_hours/unmet_hours


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    REC = {'datetime': datetime.datetime.now()}
    print BD_AVE.needsenergy(REC)
    print BD_AVE(datetime.datetime.now())
    print BD(datetime.datetime.now())
    print TV(datetime.datetime(2012, 12, 15, 20))
    print TV.bid(REC)
