"""Optimization Example

This is an example optimization of a Solar Home System

"""
from devices import Domain, IdealStorage
from devices import SimplePV, PVSystem, MPPTChargeController
from loads import annual
from caelum import eere
import numpy as np
from model import report

PLACE = (24.811468, 89.334329)

# is Pyomo an option???
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
    def __init__(self, cc, merit):
        """Test Case

        Args:
            merit (function): function to calculate merit
            cc (object):  Charge Controller

        """
        self.merit = merit
        self.cc = cc

    def __call__(self, parameters):
        size, pv = parameters
        pv = max(pv, 0)
        size = max(size, 0)
        # PLACE = (24.811468, 89.334329)
        SHS = Domain(load=annual(),
                     gen=PVSystem([self.cc([SimplePV(pv)])],
                                  PLACE, 24.81, 180.),
                     storage=IdealStorage(size))
        SHS.weather_series(eere.EPWdata('418830'))
        SHS.storage.details()
        return self.merit(SHS)


class LolhMerit(object):
    def __init__(self, lolhcost):
        self.lolhcost = lolhcost

    def __call__(self, domain):
        total = domain.cost() + domain.depletion() \
            - domain.storage.shortfall * self.lolhcost
        print total
        return total


if __name__=='__main__':
    from scipy import optimize
    merit = LolhMerit(.05)
    case1 = Case(MPPTChargeController, merit)
    # initial guess
    x0 = np.array([180., 110.])
    r = optimize.minimize(case1, x0)
    # r = optimize.basinhopping(model,x0,niter=1)
    print r
    s, p = r['x']
    #report(model((s, p)), 'mppt_p_optimized_05_lolh')
    # optimize.basinhopping(model,x0,niter=10)
    # optimize.anneal(model,x0,maxiter=10,upper=1000,lower=0)
