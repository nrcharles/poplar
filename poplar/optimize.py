"""Optimization Example.

Adjust battery capacity and pv size to minimize price of a Solar Home System
for a location.

"""

import environment as env
import logging
logging.basicConfig(level=logging.ERROR)
from devices import Gateway
from sources import SimplePV, Site, InclinedPlane
from storage import IdealStorage
from controllers import MPPTChargeController, SimpleChargeController
from caelum import eere
import numpy as np
from scipy import optimize


class Case(object):

    """Test Case.

    Attributes:
        merit (function): to calculate merit
        cc (object): Charge Controller
        load (object): Load

    """

    def __init__(self, cc, merit, load):
        """Initialize.

        Args:
            merit (function): to calculate merit
            cc (object): Charge Controller
            load (object): Load

        """
        self.merit = merit
        self.cc = cc
        self.load = load
        self.place = (24.811468, 89.334329)
        self.tilt = 24.81  # array tilted at latitude
        self.azimuth = 180.  # array pointed due south
        self.weather_station = '418830'
        self.foo = open('log.csv', 'w')

    def model(self, parameters):
        """Model a year of data for a location.

        Args:
            parameters: (tuple) capacity (Wh), PV Size (STC).

        Returns:
            (domain): results from model.
        """
        env.reset()
        size, pv = parameters
        # don't go below 1 negative/division by zero issues
        pv = max(pv, 1.)
        size = max(size, 1.)

        plane = InclinedPlane(Site(self.place), self.tilt, self.azimuth)
        load = self.load()
        SHS = Gateway([load,
                      self.cc([SimplePV(pv, plane)]),
                      IdealStorage(size)])

        for r in eere.EPWdata('418830'):
            env.update_time(r['datetime'])
            SHS()

        print SHS.details()
        self.foo.write('%s,%s,%s\n' % (size, pv, SHS.merit()))
        self.foo.flush()
        return SHS

    __call__ = lambda self, x: self.merit(self.model(x))


def mppt(load, merit):
    """Optimize MPPT system for given a load and merit.

    What is the optimum sizing of an single reliablity domain with an MPPT
    charge controller with a linear 95%  efficiency curve using a local
    minimize algorithm.

    Args:
        load : (object)
        merit : (object)

    Returns:
        (str, str): Latex markup for figure and table

    """
    case1 = Case(MPPTChargeController, merit, load)
    # initial guess
    x0 = np.array([100., 60.])

    r = optimize.minimize(case1, x0,  options={'disp': True},
                          bounds=[[5, None],
                          [5, None]], method='SLSQP')
    print r
    s, p = r['x']
    tex_tab, tex_fig = case1.model((s, p)).report()
    print tex_tab, tex_fig


def simple(load, merit):
    """Optimize Simple system for a given load and merit.

    Given a load and a merit, what is the optimum sizing of an single
    reliablity domain with an simple charge controller which is effectively
    a diode tied to a battery.

    Args:
        load : (object)
        merit : (object)

    Returns:
        (str, str): Latex markup for figure and table

    """
    case1 = Case(SimpleChargeController, merit, load)
    x0 = np.array([200., 98.])
    r = optimize.minimize(case1, x0)
    print r
    s, p = r['x']
    case1.model((s, p)).report()


if __name__ == '__main__':
    import loads
    import merit
    env.set_weather(eere.EPWdata('418830'))
    steep = merit.STEEPMerit()
    mppt(loads.Annual, steep)
