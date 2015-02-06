"""Optimization Example

This is an example optimization of a Solar Home System

"""
from devices import Domain, IdealStorage
from devices import SimplePV, PVSystem, MPPTChargeController
from loads import annual
from caelum import eere
import numpy as np

PLACE = (24.811468, 89.334329)

# SHS = Domain(load=DailyLoad([0,18,19,22,21,24],[0,0,1,1,0,0]),
# Parameters
# battery chemistry LA,LI
# charge controller Simple, MPPT
# reliablity domains
# net metering
# load profiles
# storage size
# tilt & azimuth?

class Case(object):
    """Example Test Case"""
    def __init__(self, cc, merit):
        """Test Case

        Args:
            merit (function): function to calculate merit
            cc (object):  Charge Controller

        """
        self.merit = merit
        self.cc = cc

    def model(self, parameters):
        size, pv = parameters
        pv = max(pv, 0)
        size = max(size, 0)
        # PLACE = (24.811468, 89.334329)
        SHS = Domain(load=annual(),
                     gen=PVSystem([self.cc([SimplePV(pv)])],
                                  PLACE, 24.81, 180.),
                     storage=IdealStorage(size))
        SHS.weather_series(eere.EPWdata('418830'))
        print SHS.storage.details()
        return SHS

    def __call__(self, parameters):
        """Default Method
        """
        SHS = self.model(parameters)

        return self.merit(SHS)


class LolhMerit(object):
    """Example merit class

    Merit is based on Minimum Price with Loss of Load Hours (LOLH) having a
    cost per hour.

    """
    def __init__(self, lolhcost):
        self.lolhcost = lolhcost

    def __call__(self, domain):
        total = domain.cost() + domain.depletion() \
            - domain.storage.shortfall * self.lolhcost
        print total
        return total


if __name__=='__main__':
    from scipy import optimize
    from visuals import report
    merit = LolhMerit(.05)
    case1 = Case(MPPTChargeController, merit)
    # initial guess
    x0 = np.array([180., 110.])
    #r = optimize.minimize(case1, x0)
    r = optimize.basinhopping(case1,x0,niter=2)
    print r
    s, p = r['x']
    report(case1.model((s, p)), 'mppt_p_basin_05_lolh')
