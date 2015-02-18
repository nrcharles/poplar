"""Loads

This Module contains various loads that can be used to acess system
configurations.

"""
import csv
import datetime
import numpy as np
import random
from scipy.interpolate import interp1d
from devices import Device
from econ import Bid

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


def load(filename=None):
    BD = {}
    if filename is None:
        filename = './profiles.csv'
    foo = csv.reader(open(filename))
    for i in foo:
        lp = [float(j.strip()) for j in i[2:50]]
        tdt = datetime.datetime.strptime(i[0][0:19], FMT).date()
        # , len(lp),lp
        BD[tdt] = lp
    return BD


class Load(Device):
    def bids(self, record):
        return [Bid(self.needsenergy(record), self.buy_kwh())]

    def needsenergy(self, record):
        return self.demand(record['datetime'])

    def buy_kwh(self):
        return self.value_kwh()

    def value_kwh(self):
        return self.per_kwh

    def droopable(self, record):
        return 0.


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
        """
        Parameters:
            mult (float): scaling factor (default 71.4)
            year (int): (default 2013)

        """
        self.mult = mult
        self.classification = "load"
        self.deferable = False
        self.year = year
        self.per_kwh = 0.07
        self.data = load()

    def demand(self, dt):
        """ Demand at time.

        >>> BD = Annual(100.)
        >>> round(BD(datetime.datetime(2014, 12, 16, 20)),1)
        11.7

        >>> round(BD(datetime.datetime(2014, 1, 16, 3)), 1)
        7.2

        Args:
            dt (datetime)

        Returns:
            (float) Wh

        """
        mdt = datetime.date(self.year, dt.month, dt.day)
        offset = int(round(dt.hour*2.0))
        return self.data[mdt][offset]*self.mult/40812.5

    __call__ = demand

    def total(self):
        """Total Load for Year

        >>> BD = Annual(100.)
        >>> round(BD.total(), 1)
        100000.0


        Returns:
            (float) Wh

        """
        return sum(self(hour_to_dt(i)) for i in range(365*24))

    def __repr__(self):
        return '%s kWh Annual' % round(self.total()/1000., 1)


class DailyLoad(Load):
    """Spline interpolated Load Profile"""
    def __init__(self, hours, loads, kind='cubic', name='Daily Load'):
        self.profile = interp1d(hours, loads, kind=kind)
        self.name = name
        self.classification = "load"
        self.deferable = False
        self.dimmable = False
        self.per_kwh = 0.07

    def demand(self, dt):
        return self.profile(dt.hour + dt.minute/60.)

    def total(self):
        return sum([self(hour_to_dt(i)) for i in range(24)])

    __call__ = demand

    def __repr__(self):
        return "%s %s wH Daily" % (self.name, round(self.total(), 1))

times = np.array(range(0, 49))/2.
spline_profile = DailyLoad(times, np.array(LOAD_PROFILE)*17)

TV_L = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 20, 20, 20,
        20, 0, 0]
TV_H = range(25)
TV = DailyLoad(TV_H, TV_L, kind='linear', name='12" B&W TV')

FLAT = DailyLoad([0,25],[8.15, 8.15], kind='linear', name ='Flat')

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
    """How much of a load can be met by sunlight

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
