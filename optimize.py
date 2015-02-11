"""Optimization Example:

Adjust battery capacity and pv size to minimize price of a Solar Home System
for a location.

"""
from devices import Domain, SimplePV, PVSystem
from storage import IdealStorage
from controllers import MPPTChargeController, SimpleChargeController
from loads import annual
from caelum import eere
import numpy as np
from scipy import optimize
from visuals import report

# Parameters that could be tested
# battery chemistry LA,LI
# charge controller Simple, MPPT
# reliablity domains
# net metering
# various load profiles
# enhanced DSM
# storage size
# tilt & azimuth


class Case(object):
    """Test Case

    Attributes:
        merit (function): to calculate merit
        cc (object): Charge Controller
        load (object): Load

    """
    def __init__(self, cc, merit, load):
        """
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

    def model(self, parameters):
        """Model a year of data for a location

        Args:
            parameters: (tuple) capacity (wH), PV Size (STC).

        Returns:
            (domain): results from model.
        """
        size, pv = parameters
        # don't go below 1 negative/division by zero issues
        pv = max(pv, 1)
        size = max(size, 1)

        SHS = Domain([self.load(),
                      PVSystem([self.cc([SimplePV(pv)])],
                               self.place, self.tilt, self.azimuth),
                      IdealStorage(size)])
        SHS.weather_series(eere.EPWdata(self.weather_station))
        print SHS.details()
        return SHS

    # default method
    __call__ = lambda self, x: merit(self.model(x))


class EnergyMerit(object):
    """Example merit class based on Energy Shortfall

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
    """Example merit class based on Loss of Load Hours

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


class TMerit(object):
    """Example merit class based on Impact

    Merit is based on Minimum CO2 emissions and Loss of Load Hours (LOLH)

    """
    def __init__(self):
        pass

    def __call__(self, domain):
        total = domain.co2() * (1+domain.lolh)
        print total
        return total

    def __repr__(self):
        return 'test_merit'


def mppt(load, merit):
    """Optimize MPPT system

    Given a load and a merit, what is the optimum sizing of an single
    reliablity domain with an MPPT charge controller with a linear 95%
    effciency curve using a local minimize algorithm.

    Args:
        load : (object)
        merit : (object)

    Returns:
        (str, str): Latex markup for figure and table

    """
    case1 = Case(MPPTChargeController, merit, load)
    # initial guess
    x0 = np.array([180., 110.])
    # r = optimize.basinhopping(case1, x0, niter=3)
    r = optimize.minimize(case1, x0)
    print r
    s, p = r['x']
    tex_tab, tex_fig = report(case1.model((s, p)), 'mppt_min_%s' % merit)
    print tex_tab, tex_fig


def simple(load, merit):
    """Optimize Simple system

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
    x0 = np.array([180., 110.])
    # Basin-hopping is a stochastic algorithm which attempts to find the global
    # minimum of a smooth scalar function of one or more variables
    r = optimize.minimize(case1, x0)
    print r
    s, p = r['x']
    report(case1.model((s, p)), 'simple_min_%s' % merit)


if __name__ == '__main__':
    merit = LolhMerit(0.07)
    mppt(annual, merit)
    # simple(annual, merit)
