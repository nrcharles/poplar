"""Merit calculation classes."""

import logging
logging.basicConfig(level=logging.ERROR)


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


class STEEPMerit(object):

    """Social Technology Economic Environmental Political (STEEP) merit."""

    def __init__(self, life=5.):
        self.life = life

    def merit(self, domain):
        """Social Technology Economic Environmental Political (STEEP) merit.

        Smaller values are indicate higher merit M.

        .. math:: M = \\text{C} + y\\cdot \\text{D} + I_{m} + y\\cdot I_{P} + r\\cdot p

        Where C is the cost of the system hardware parts, y is years, D is
        depletion expense, Im is manufacturing environment impact, Ip is
        environment impact from prospective system use, and r is a weighted
        performance based penalty.  In this case I is (kg CO2 eq) and r
        is (wH * domain_r).
        """
        total = (domain.cost() +
                 domain.depletion()*self.life +
                 domain.co2() +
                 domain.parameter('emissions')*self.life -
                 domain.rvalue())

        logging.debug('merit %s', total)
        return total

    __call__ = merit

    def __repr__(self):
        return 'STEEP Merit (%s year life)' % self.life


class TotalMerit(object):

    """Example merit class based on Carbon Impact.

    Merit is based on Minimum CO2 emissions and Loss of Load Hours (LOLH)

    """

    def __init__(self):
        pass
        # .543 kg/kWh
        self.penalty = .543/1000.0 * 5  # 5 year life

    def __call__(self, domain):
        total = domain.steep()
        print total, domain.cost(), domain.depletion()*5, domain.shortfall, \
            domain.co2(), domain.parameter('emissions')*5
        return total

    def __repr__(self):
        return 'test_merit'
