"""Optimization Example.

Adjust battery capacity and pv size to minimize price of a Solar Home System
for a location.

"""

import environment as env
import copy
import logging
logging.basicConfig(level=logging.ERROR)
from devices import Gateway
from sources import SimplePV, Site, InclinedPlane
from storage import IdealStorage
from controllers import MPPTChargeController, SimpleChargeController
from caelum import eere
import numpy as np
from scipy import optimize
import sys


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
            parameters: (tuple) capacity (wH), PV Size (STC).

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
        print SHS.network.nodes()
        for r in eere.EPWdata('418830'):
            env.update_time(r['datetime'])
            SHS()
        print load.enabled()
        print sum(load.balance.values())
        print id(load)
        d = SHS.details()
        print d
        self.foo.write('%s,%s,%s\n' % (size, pv, d['t']))
        # self.foo.flush()
        return SHS

    # default method
    __call__ = lambda self, x: merit(self.model(x))


class EnergyMerit(object):

    """Example merit class based on Energy Shortfall.

    Merit is based on Minimum Price with Energy having a kWh cost.

    """

    def __init__(self, lolhcost):
        self.lolhcost = lolhcost

    def __call__(self, domain):
        total = domain.cost() + domain.depletion() \
            + domain.shortfall * self.lolhcost
        print domain.shortfall, total
        return total

    def __repr__(self):
        return 'energy_%s' % self.lolhcost


class LolhMerit(object):

    """Example merit class based on Loss of Load Hours.

    Merit is based on Minimum Price with Loss of Load Hours (LOLH) having a
    cost per hour.

    """

    def __init__(self, lolhcost):
        self.lolhcost = lolhcost

    def __call__(self, domain):
        total = domain.cost() + domain.depletion() \
            + domain.lolh * self.lolhcost
        print domain.lolh, total
        return total

    def __repr__(self):
        return 'lolh_%s' % self.lolhcost


class TotalMerit(object):

    """Example merit class based on Carbon Impact.

    Merit is based on Minimum CO2 emissions and Loss of Load Hours (LOLH)

    """

    def __init__(self):
        pass
        # .543 kg/kWh
        self.penalty = .543/1000.0 * 5  # 5 year life

    def __call__(self, domain):
        total = domain.details()['t']
        print total, domain.cost(), domain.depletion()*5, domain.shortfall, \
            domain.co2(), domain.parameter('emissions')*5
        return total

    def __repr__(self):
        return 'test_merit'


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
    x0 = np.array([80., 60.])

    # minimizer_kwargs={'method':'SLSQP','options':{'disp':True}})
    # r = optimize.basinhopping(case1, x0, disp=True,
    # minimizer_kwargs={'method':'SLSQP','args':('options',{'disp':True})})
    r = optimize.minimize(case1, x0, options={'disp': True}, bounds=[[5, None],
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
    # initial guess
    x0 = np.array([200., 98.])
    # Basin-hopping is a stochastic algorithm which attempts to find the global
    # minimum of a smooth scalar function of one or more variables
    r = optimize.minimize(case1, x0)
    print r
    s, p = r['x']
    case1.model((s, p)).report()


if __name__ == '__main__':
    import loads
    env.set_weather(eere.EPWdata('418830'))
    # merit = LolhMerit(1.0)
    merit = TotalMerit()
    mppt(loads.Annual, merit)
    # mppt(annual(), merit)
    # simple(annual, merit)
    # merit = LolhMerit(0.07)
    # mppt(annual, merit)
