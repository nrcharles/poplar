import numpy as np
import networkx as nx
from misc import significant, Counter
from econ import high_bid, low_offer

import logging
logger = logging.getLogger(__name__)

SMALL_ID = Counter()

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
        if hasattr(self, 'children'):
            for i in self.children:
                if not hasattr(self, 'network'):
                    self.network = i.graph()
                    self.network.add_node(self)
                    self.network.add_edge(self,i)
                    print self.network.edges()
                else:
                    c = i.graph()
                    self.network.add_nodes_from(c.nodes())
                    self.network.add_edges_from(c.edges())
                    self.network.add_edge(self, i)
                    i.network = self.network
        if not hasattr(self,'network'):
            self.network = nx.Graph()
            self.network.add_node(self)

        return self.network

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
        self.small_id = SMALL_ID.next(type(self))
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
        self.source = {}
        self.lolh = 0.
        self.r = 1.
        self.network = self.graph()

    def autonomy(self):
        """Calculate domain autonomy.

        Returns:
            (float) hours

        Note: assumes hour time intervals

        """
        # g_ave = sum(self.g)/len(self.g)
        l_median = np.median(self.log_dict_to_list('demand'))
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

    def log_dict_to_list(self, log_dict, default=0):
        return [getattr(self, log_dict).setdefault(i,default)
                for i in self.time_series]

    def details(self):
        """Create dict of metrics."""
        results = {
            'Demand (wh)': significant(sum(self.log_dict_to_list('demand'))),
            'Net (wh)': significant(sum(self.log_dict_to_list('balance'))),
            'Domain Sources(wh)': significant(sum(self.log_dict_to_list('source'))),
            'Domain credits(wh)': significant(sum(self.log_dict_to_list('credits'))),
            'Domain dedits(wh)': significant(sum(self.log_dict_to_list('debits'))),
            'Domain Generation losses (wh)':
            significant(self.parameter('losses')),
            # 'Autonomy (hours) (Median Load/C)': significant(self.autonomy()),
            # 'Capacity Factor (%)': significant(self.capacity_factor()*100.),
            'Domain surplus (Wh)': significant(self.surplus),
            # 'Domain Generation (Wh)': significant(sum(self.g)),
            'Domain Parts (USD)': significant(self.cost()),
            'Domain depletion (USD)': significant(self.depletion()),
            'Domain lolh (hours)': significant(self.lolh),
            'Domain outages (n)': significant(self.outages),
            'A (m2)': significant(self.parameter('area')),
            'Toxicity (CTUh)': significant(self.tox()),
            'CO2 (kgCO2 eq)': significant(self.co2()),
            # 'Domain Efficiency (%)': significant(self.eta()*100),
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

    def reconcile(self, record):
        key = record['datetime']
        for child in self.children:
            if type(child) == Domain:
                # print self.balance[key], self.credits[key], self.debits[key], self.balance[key]
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

    def transaction(self, offer, bid, record):
        # transer energy from destination bid to source offer
        key = record['datetime']
        delta = min(abs(self.balance[key]),offer.wh)
        dest = self.select_node(bid.obj_id)
        # add to bid destination
        dest.power_io(delta, record)
        #self.demand[key] += delta
        self.balance[key] += delta
        self.credits[key] += delta
        # subtract from offer source
        source = self.select_node(offer.obj_id)
        source.power_io(-delta, record)
        source_domain = self.select_domain(offer.obj_id)
        source_domain.debits[key] -= delta
        source_domain.balance[key] -= delta
        # subtracting from source ,adding to self
        # -7.17085342045 14.4358005547
        # -21.6066539751 28.8716011093
        logger.info('%s: Transfered %s wH from %s toward %s wH in %s',
                    key, delta, source, bid.wh, dest)
        return True

    def get_energy(self, record, bid):
        # energy auction
        key = record['datetime']
        initial_demand = self.demand[key]
        node = self.select_node(bid.obj_id)
        logger.debug("New auction %s for %s wH" , key, initial_demand)
        offer = low_offer(self.network, record, bid)
        while offer and node.needsenergy(record):
            logger.debug('High bid %s' , bid)
            logger.debug('Low Offer %s' , offer)
            self.transaction(offer, bid, record)
            offer = low_offer(self.network, record, bid)

        # account for shortage
        if self.balance[key] != 0. and not bid.storage:
            logger.debug("Shortfall of %s, in %s", self.balance[key], self)
            self.outages += 1
            self.shortfall += self.demand[key]
            self.lolh += (initial_demand - self.balance[key])/initial_demand * \
                self.timestep
            return False
        return True

    def connected_domains(self):
        # isdomain = lambda x: (type(x) is Domain) and (x is not self)
        isdomain = lambda x: (type(x) is Domain)
        return filter(isdomain, self.network)

    def select_domain(self,obj_id):
        for node in self.network:
            if id(node) == obj_id:
                for neighbor in node.network.neighbors(node):
                    # should only be in one Domain
                    # should only have one neighbor
                    if type(neighbor) is Domain:
                        return neighbor
        raise KeyError('%s not found' % obj_id)

    def select_node(self,obj_id):
        for node in self.network:
            if id(node) == obj_id:
                return node
        raise KeyError('%s not found' % obj_id)

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
        key = record['datetime']

        logger.debug('Start processsing %s' , key)
        #init 
        for node in self.connected_domains():
            node.timestep = hours
            node.time_series.append(key)
            node.credits[key] = 0.
            node.demand[key] = 0.
            node.debits[key] = 0.
            node.balance[key] = 0.

        # total non-droopable energy demand

        for node in self.connected_domains():
            node_dmnd = node.needsenergy(record) * (1. - node.droopable(record))
            node.demand[key] = node.demand.setdefault(key, 0) + node_dmnd

        # total energy with curtailment penalties
        for node in self.connected_domains():
            node.source[key] = node.hasenergy(record) * node.curtailment_ratio(record)

        for node in self.connected_domains():
            # demands are always negative
            node.balance[key] = node.source[key] + node.demand[key]

        # rebalance power neglecting transmission costs/constraints
        # find demand with highest priority
        bid = high_bid(self.network, record)
        if not bid:
            logger.info('%s no bids.', key)

        offer = low_offer(self.network, record, bid)
        if not offer:
            logger.info('%s no offers.', key)

        # print "are you selling to yourself? "
        # print "are we transfering energy from battery to battery"?
        # print bid, offer
        while bid and offer:
            logger.debug('highest priority energy: %s', bid)
            dest = self.select_domain(bid.obj_id)
            logger.debug('Transfering control to %s' , dest)
            dest.get_energy(record, bid)
            bid = high_bid(self.network, record)
            offer = low_offer(self.network, record, bid)

        # distribute excess energy
        #    bid = high_bid
        #            node.send_energy(record)

        # reconcile shortages/surpluses 
        self.reconcile(record)
        # return net

    def needsenergy(self, record):
        e = 0
        for i in self.children:
            if hasattr(i, 'needsenergy') and type(i) is not Domain:
                e += i.needsenergy(record)
        return e

    def hasenergy(self, record):
        e = 0
        for i in self.children:
            if hasattr(i, 'hasenergy') and type(i) is not Domain:
                e += i.hasenergy(record)
        return e

    def droopable(self, record):
        # todo: test this code
        e = 0.
        d = 0.
        for i in self.children:
            if hasattr(i, 'needsenergy') and type(i) is not Domain:
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
            if hasattr(i, 'hasenergy') and type(i) is not Domain:
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
                m_v = min(m_v, i.buy_kwh())
        return m_v

    def sell_kwh(self):
        m_v = 0
        for i in self.children:
            if hasattr(i, 'sell_kwh'):
                m_v = max(m_v, i.sell_kwh())
        return m_v

    def depletion(self):
        return self.parameter('depletion')

    def rvalue(self):
        return self.r*self.outages

    __call__ = calc

    def __repr__(self):
        return 'Domain %s, %s Outages' % (self.small_id, self.outages) # significant(self.cost())


if __name__ == '__main__':
    import doctest
    doctest.testmod()
