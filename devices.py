import numpy as np
import networkx as nx
from misc import significant

class Device(object):

    """
    Device LCA Object.

    The premise of this tool is that Devices have LCA values.  This class is
    inherited to create the modeling framework.

    Attributes:
        children: (list) list of children.
        device_co2: (float) kg co2 eq footprint.
        device_tox: (float) device toxicity.
        device_cost: (float) device cost.

    """

    def __init__(self):
        """Method should be overridden."""
        self.children = []
        self.device_cost = 0.
        self.device_tox = 0.
        self.device_co2 = 0.
        self.device_area = 0.

    def parameter(self, name):
        """Default parameter method.

        Accounts for arbitrary attributes on Device objects.

        Args:
            name (string): name of parameter function.

        Returns:
            (float): sum of parameter for all decendants.

        """
        # This is redundant with node_iter
        v = 0.
        if hasattr(self, 'children'):
            for i in self.children:
                if hasattr(i, name):
                    v += getattr(i, name)()
        if hasattr(self, 'device_%s' % name):
            v += getattr(self, 'device_%s' % name)
        return v

    def co2(self):
        """CO2 eq footprint.

        Returns:
            (float): kg CO2 eq.
        """
        return self.parameter('co2')

    def tox(self):
        """Toxicity footprint.

        Returns:
            (float): CTUh
        """
        return self.parameter('tox')

    def cost(self):
        """Device cost.

        Returns:
            (float): USD
        """
        return self.parameter('cost')

    def area(self):
        """Device footprint.

        Returns:
            (float): m^2
        """
        return self.parameter('area')

    def graph(self):
        """Device Graph of all decendant devices.

        Returns:
            (Graph)
        """
        G = nx.Graph()
        G.add_node(self)
        if hasattr(self, 'children'):
            for i in self.children:
                G.add_node(i)
                G.add_edge(self, i)
                G = nx.compose(G, i.graph())
        return G

    def __repr__(self):
        return 'Device'

class Domain(Device):

    """Base Domain Class.

    Attributes:
        g: (list) total gen delivered to domain.
        l: (list) desired load.
        d: (list) delta energy; surplus or shortfall.
        children: (list) devices in domain.
        net_l: (list) enabled load (wH).
        loss_occurence: (int) loss (wH).
        surplus: (float) total excess energy (wH).
        shortfall: (float) total energy shortfall (wH).
    """

    def __init__(self, children=None):
        """Should have at least one child but should probably have two.

        Args:
            children (list): loads, storage, and generation
        """
        # super(Device, self).__init__()
        self.children = children
        self.g = []
        self.l = []
        self.d = []
        self.state_series = []
        self.hours = []
        self.time_series = []
        self.outages = 0
        self.net_g = []  # used generation
        self.net_l = []  # enabled load
        self.surplus = 0.
        self.shortfall = 0.
        self.credits = {}
        self.debits = {}
        self.balance = {}
        self.demand = {}
        self.lolh = 0.
        self.r = 1.

    def td(self):
        return sum([self.demand[i] for i in self.time_series])

    def autonomy(self):
        """Calculate domain autonomy.

        Returns:
            (float) hours

        Note: assumes hour time intervals

        """
        # g_ave = sum(self.g)/len(self.g)
        l_median = np.median(self.l)
        return self.capacity()/l_median  # hours

    def eta(self):
        """Calculate domain efficiency.

        Returns:
            (float) dimensionless

        .. math:: \\eta_{T} = \\frac{\\sum{Loads}}{\\sum{Generation}}


        """
        return sum(self.net_l)/(sum(self.g) + self.parameter('losses'))

    def capacity(self):
        """Total capacity of energy storage."""
        return self.parameter('capacity')

    def capacity_factor(self):
        """Capacity Factor Cf

        .. math:: C_{f} = \\frac{\\sum{Loads}}{G_{P}\\cdot 365 \\cdot 24}

        Where Gp is peak generation

        """
        if self.STC():
            return sum(self.net_l)/(self.STC()*24*365)
        else:
            return 0.

    def details(self):
        """Create dict of metrics."""
        results = {
            'Desired load (wh)': significant(sum(self.l)),
            'Domain Generation losses (wh)':
            significant(self.parameter('losses')),
            'Autonomy (hours) (Median Load/C)': significant(self.autonomy()),
            'Capacity Factor (%)': significant(self.capacity_factor()*100.),
            'Domain surplus (Wh)': significant(self.surplus),
            'Domain Generation (Wh)': significant(sum(self.g)),
            'Domain Parts (USD)': significant(self.cost()),
            'Domain depletion (USD)': significant(self.depletion()),
            'Domain lolh (hours)': significant(self.lolh),
            'Domain outages (n)': significant(self.outages),
            'A (m2)': significant(self.parameter('area')),
            'Toxicity (CTUh)': significant(self.tox()),
            'CO2 (kgCO2 eq)': significant(self.co2()),
            'Domain Efficiency (%)': significant(self.eta()*100),
            'STC (w)': self.STC()
        }
        return results

    def STC(self):
        """STC nameplate rating of all generation in domain."""
        nameplate = 0
        for child in self.children:
            if hasattr(child, 'gen'):
                if child.gen:
                    nameplate += child.nameplate()
        return nameplate

    def weather_series(self, array_like):
        for i in array_like:
            self(i)

    def energy_source(self, record):
        """Find cheapest energy source.

        hasenergy and sell_kwh makes up an offer.

        Returns:
            (object): Device or Domain to cover energy shortfall.
        """
        min_kwh_c = 10
        choice = None
        # select lowest energy source bid
        for child in self.children:
            if hasattr(child, 'power_io'):
                if child.hasenergy(record) and child.sell_kwh() < min_kwh_c:
                    choice = child
                    min_kwh_c = child.sell_kwh()
        return choice

    def energy_sink(self, record):
        """Find most expensive energy sink.

        needsenergy and buy_kwh makes up a bid

        Returns:
            (object): Device or Domain for energy transfer
        """
        # prioritize energy storage
        min_kwh_c = 0
        choice = None
        # Select highest bid for energy value
        for child in self.children:
            if hasattr(child, 'power_io'):
                if child.needsenergy(record) and child.buy_kwh() > min_kwh_c:
                    choice = child
                    min_kwh_c = child.buy_kwh()
        return choice

    def reconcile(self, record):
        key = record['datetime']
        for child in self.children:
            if type(child) == Domain:
                print self.balance[key], self.credits[key], self.debits[key], self.balance[key]
                if self.balance[key]:
                    pass


    def power_io(self, energy, record):
        """Bank energy."""
        net = 0
        # demand = self.l[-1]  # may be wrong
        key = record['datetime']
        if energy >= 0:
            self.credits[key] = self.credits.setdefault(key, 0) + energy
        if energy < 0:
            self.debits[key] = self.debits.setdefault(key, 0) + energy
        self.balance[key] = self.balance.setdefault(key, 0) + energy
        #demand = self.needsenergy(record) * (1 - self.droopable(record))
        demand = self.demand[key]

        if energy >= 0:
            net = self.deposit(energy, record)
        if energy < 0:
            net = self.withdraw(energy, record)

        if net > 0:  # net > 0 is surplus energy
            self.surplus += net

        if net < 0:  # net < 0 is energy shortfall
            self.shortfall -= net
            self.outages += 1
            self.lolh += net / - demand

        self.d.append(net)
        self.net_l.append(min(demand + net, demand))

        energy_stored = 0.
        nominal_capacity = 0.
        for child in self.children:
            if hasattr(child, 'state'):
                energy_stored += child.state
            if hasattr(child, 'nominal_capacity'):
                nominal_capacity += child.nominal_capacity

        if nominal_capacity == 0.:
            self.state_series.append(energy_stored)
        else:
            state = energy_stored/nominal_capacity
            self.state_series.append(state)

        return net

    def deposit(self, energy, record):
        """Store surplus energy in a domain.

        Args:
            energy_surplus: (float) positive in (wH)

        Returns:
            (float): (wH) surplus that couldn't be transferred.
        """
        # energy is surplus (positive)
        storage = self.energy_sink(record)
        while storage and energy > 0:
            a = storage.needsenergy(record)
            delta = min(a, energy)
            storage.power_io(delta, record)
            energy -= delta
            storage = self.energy_sink(record)

        return energy

    def withdraw(self, energy, record):
        """Withdraw energy from a domain to cover a shortfall.

        Args:
            energy_shortfall(float): negative, energy (wH) needed.

        Returns:
            (float): wH shortfall that couldn't be covered.
        """
        # energy is shortfall (negative)
        source = self.energy_source(record)
        while source and energy < 0:
            a = source.hasenergy(record)
            delta = min(a, abs(energy))
            source.power_io(-delta, record)
            energy += delta
            source = self.energy_source(record)

        return energy

    def calc(self, record, hours=1.0):
        """Calculate energy for data record.

        Domains behave like a an energy market, excess energy is are transfered
        to the device with the highest bid and energy shortfalls are covered
        from the device with the lowest offer.

        Args:
            record(dict): record of weather data and time.

        Returns:
            (float): net energy surplus or shortfall (wH).

        """
        self.hours.append(hours)
        # print record['datetime']
        key = record['datetime']
        # self.time_series.append(key)

        # total non-droopable energy demand

        for node in self.graph():
            if type(node) == Domain:
                node_dmnd = node.needsenergy(record) * (1. - node.droopable(record))
                node.demand[key] = node.demand.setdefault(key, 0) + node_dmnd
                # print id(node), node.demand[key], node.needsenergy(record), node.droopable(record), node_dmnd
                # init
                node.time_series.append(key)
                node.credits[key] = 0.
                node.debits[key] = 0.
                node.balance[key] = 0.

        demand = self.demand[key]

            # if child.classification == 'load':
                # demand += child(record['datetime'])

        # total energy with curtailment penalties
        source = 0
        for node in self.graph():
            if type(node) == Domain:
                node.balance[key] += node.hasenergy(record) * node.curtailment_ratio(record)

        for child in self.children:
            if hasattr(child, 'hasenergy'):
                source += child.hasenergy(record) * child.curtailment_ratio(record)
        #print source, self.balance[key]
            # if child.classification == 'source':
            #    source += child(record)

        self.g.append(source)
        self.l.append(demand)

        delta = source - demand
        # reconcile energy shortages

        net = self.power_io(delta, record)
        #self.reconcile(record)
        return net

    def needsenergy(self, record):
        e = 0
        for i in self.children:
            if hasattr(i, 'needsenergy'):
                e += i.needsenergy(record)
        return e

    def hasenergy(self, record):
        e = 0
        for i in self.children:
            if hasattr(i, 'hasenergy'):
                e += i.hasenergy(record)
        return e

    def droopable(self, record):
        # todo: test this code
        e = 0.
        d = 0.
        for i in self.children:
            if hasattr(i, 'needsenergy'):
                ce = i.needsenergy(record)
                cd = i.droopable(record)
                d += ce*cd
                e += ce
        # print d,e
        if e:
            # print d/e
            return d/e
        else:
            return 0.

    def curtailment_ratio(self, record):
        # todo: fix this code
        e = 0.
        c = 0.
        # return 0.
        for i in self.children:
            if hasattr(i, 'hasenergy'):
                ce = i.hasenergy(record)
                cc = i.curtailment_ratio(record)
                c += ce*cc
                e += ce
        if e:
            # print c/e
            return c/e
        else:
            return 0.

    def buy_kwh(self):
        # return 0.07
        m_v = 0
        for i in self.children:
            if hasattr(i, 'buy_kwh'):
                m_v = max(m_v, i.buy_kwh())
        return m_v

    def depletion(self):
        return self.parameter('depletion')

    def rvalue(self):
        return self.r*self.outages

    __call__ = calc

    def __repr__(self):
        return 'Domain %s Outages' % self.outages # significant(self.cost())


if __name__ == '__main__':
    import doctest
    doctest.testmod()
