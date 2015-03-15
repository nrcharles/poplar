import numpy as np
import networkx as nx
import environment as env
from misc import significant, Counter
from econ import high_bid, low_offer, rank_bids
from visuals import multi_report

import logging
logger = logging.getLogger(__name__)

SMALL_ID = Counter()


class Seed(object):
    def graph(self):
        """Device Graph of all decendants.

        Returns:
            (Graph)
        """

        # todo: this code could use some polishing

        if not hasattr(self, 'network'):
            # find an existing network graph
            if env.network:
                self.network = env.network
                self.network.add_node(self)
            else:
                self.network = nx.Graph()
                self.network.add_node(self)
                env.network = self.network

        if hasattr(self, 'children'):
            for i in self.children:
                c = i.graph()
                if c != self.network:
                    self.network.add_nodes_from(c.nodes())
                    self.network.add_edges_from(c.edges())
                    self.network.add_edge(self, i)
                    for node in i.network:
                        node.network = self.network
                else:
                    self.network.add_edge(self, i)

        return self.network

    def connected_domains(self):
        # isdomain = lambda x: (type(x) is Domain) and (x is not self)
        isdomain = lambda x: (type(x) is Domain)
        return filter(isdomain, self.network)

    def dest_gateway(self, obj_id):
        """find dest obj_id's input gateway

        Returns:
            Domain
        """

        node = self.find_node(obj_id)
        for step in reversed(self.path(node)):
            if type(step) is Domain:
                return step
        print 'dest', obj_id, 'self', id(self)
        print self.path(node)
        raise KeyError('Gateway for %s not found' % obj_id)

    def src_gateway(self, obj_id):
        """find output gateway from self to dest obj_id

        Returns:
            Domain
        """
        node = self.find_node(obj_id)
        for step in self.path(node):
            if type(step) is Domain:
                return step
        print obj_id, id(self)
        print self.path(node)
        raise KeyError('Gateway for %s not found' % obj_id)

    def find_node(self, obj_id):
        for node in self.network:
            if id(node) == obj_id:
                return node
        for i in self.network:
            print i, id(i)

        raise KeyError('Node %s not found' % obj_id)

    def path(self, node):
        return nx.shortest_path(self.network, self, node)


class Device(Seed):

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
        self.net_g = []  # used generation
        self.net_l = []  # enabled load
        self.surplus = 0.
        self.shortfall = 0.
        self.credits = {}
        self.debits = {}
        self.balance = {}
        self.demand = {}
        self.outage = {}
        self.source = {}
        self.lolh = 0.
        self.r = 1.
        self.network = self.graph()
        self.export_power = True

    def autonomy(self):
        """Calculate domain autonomy.

        Returns:
            (float) hours

        Note: assumes hour time intervals

        """
        # g_ave = sum(self.g)/len(self.g)
        l_median = np.median(self.log_dict_to_list('demand'))
        return self.capacity()/l_median  # hours

    def report(self):
        return multi_report(self, str(self))

    def eta(self):
        """Calculate domain efficiency.

        Returns:
            (float) dimensionless

        .. math:: \\eta_{T} = \\frac{\\sum{Loads}}{\\sum{Generation}}


        """
        net_l = 0.
        g = 0.
        for node in self.network.nodes():
            if hasattr(node, 'enabled'):
                net_l += node.enabled()
            if hasattr(node, 'total_gen'):
                g += node.total_gen()

        return net_l/g

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

    def export(self, state=None):
        if state is not None:
            self.export_power = state
        return self.export_power

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
            'Domain debits(wh)': significant(sum(self.log_dict_to_list('debits'))),
            'Domain Generation losses (wh)':
            significant(self.parameter('losses')),
            # 'Autonomy (hours) (Median Load/C)': significant(self.autonomy()),
            # 'Capacity Factor (%)': significant(self.capacity_factor()*100.),
            'Domain surplus (Wh)': significant(self.surplus),
            # 'Domain Generation (Wh)': significant(sum(self.g)),
            'Domain Parts (USD)': significant(self.cost()),
            'Domain depletion (USD)': significant(self.depletion()),
            'Domain lolh (hours)': significant(self.lolh),
            'Domain outages (n)': significant(sum(self.outage.values())),
            'Domain shortfall (wH)': significant(self.shortfall),
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

    def reconcile(self):
        key = env.time
        for child in self.children:
            if type(child) == Domain:
                # print self.balance[key], self.credits[key],
                # self.debits[key], self.balance[key]
                if self.balance[key]:
                    pass

    def transaction(self, offer, bid):
        # transer energy from destination bid to source offer
        key = env.time
        dest = self.find_node(bid.obj_id)
        delta = min(abs(dest.needsenergy()), offer.wh)
        if delta == 0.:
            logger.error('Transaction for 0, offer was %s', offer)
        # add to bid destination
        dest.power_io(delta)
        # self.demand[key] += delta
        self.balance[key] += delta
        self.credits[key] += delta
        # subtract from offer source
        source = self.find_node(offer.obj_id)
        source.power_io(-delta )
        source_domain = self.dest_gateway(offer.obj_id)
        source_domain.debits[key] -= delta
        source_domain.balance[key] -= delta
        logger.info('%s: Transfered %s wH from %s toward %s wH in %s',
                    key, delta, source, bid.wh, dest)
        return True

    def get_energy(self, bid):
        # energy auction
        key = env.time
        node = self.find_node(bid.obj_id)
        # initial_demand = node.needsenergy()
        initial_demand = self.demand[key]
        logger.debug("New auction %s for %s wH", key, initial_demand)
        offer = low_offer(self.network, bid)
        while offer and node.needsenergy():
            logger.debug('High bid %s, Low Offer %s', bid, offer)
            self.transaction(offer, bid)
            offer = None
            offer = low_offer(self.network, bid)

        # account for shortage
        if node.needsenergy() != 0. and not bid.storage:
            # print self.balance[key], bid.storage
            logger.warning("Shortfall of %s, in %s for %s", self.balance[key],
                           self, node)
            self.outage[env.time] = 1
            self.shortfall += node.needsenergy()
            # todo: there might be a bug here
            # self.lolh += self.timestep - (initial_demand - node.needsenergy())\
            self.lolh += self.timestep - (initial_demand - self.demand[key]) \
                    /initial_demand * self.timestep
            return False
        return True

    def calc(self, hours=1.0):
        """Calculate energy.

        Domains behave like a an energy market, excess energy is are transfered
        to the device with the highest bid and energy shortfalls are covered
        from the device with the lowest offer.

        Args:
            hours (float):

        Returns:
            (float): net energy surplus or shortfall (wH).

        """
        self.hours.append(hours)
        key = env.time

        logger.debug('Start processsing %s', key)
        # init
        for node in self.connected_domains():
            node.timestep = hours
            node.time_series.append(key)
            node.credits[key] = 0.
            node.demand[key] = 0.
            node.debits[key] = 0.
            node.balance[key] = 0.

        # total non-droopable energy demand

        for node in self.connected_domains():
            node_dmnd = node.needsenergy() * (1.-node.droopable())
            node.demand[key] = node.demand.setdefault(key, 0) + node_dmnd

        # total energy with curtailment penalties
        for node in self.connected_domains():
            node.source[key] = node.hasenergy() * node.curtailment_ratio()

        for node in self.connected_domains():
            # demands are always negative
            node.balance[key] = node.source[key] + node.demand[key]

        # rebalance power neglecting transmission costs/constraints
        # find demand with highest priority
        bids = rank_bids(self.network)
        if len(bids) == 0:
            logger.info('%s no bids.', key)

        for bid in bids:
            logger.debug('current energy priority: %s', bid)
            dest = self.dest_gateway(bid.obj_id)
            logger.debug('Transfering control to %s', dest)
            dest.get_energy(bid)

        # self.reconcile()

    def needsenergy(self):
        e = 0
        for i in self.children:
            if hasattr(i, 'needsenergy') and type(i) is not Domain:
                e += i.needsenergy()
        return e

    def hasenergy(self):
        e = 0
        for i in self.children:
            if hasattr(i, 'hasenergy') and type(i) is not Domain:
                e += i.hasenergy()
        return e

    def droopable(self):
        # todo: test this code
        e = 0.
        d = 0.
        for i in self.children:
            if hasattr(i, 'needsenergy') and type(i) is not Domain:
                ce = i.needsenergy()
                cd = i.droopable()
                d += ce*cd
                e += ce
        # print d,e
        if e:
            # print d/e
            return d/e
        else:
            return 0.

    def curtailment_ratio(self):
        # todo: fix this code
        e = 0.
        c = 0.
        # return 0.
        for i in self.children:
            if hasattr(i, 'hasenergy') and type(i) is not Domain:
                ce = i.hasenergy()
                cc = i.curtailment_ratio()
                c += ce*cc
                e += ce
        if e:
            # print c/e
            return c/e
        else:
            return 0.

    def depletion(self):
        return self.parameter('depletion')

    def rvalue(self):
        return self.r*self.outages

    __call__ = calc

    def __repr__(self):
        return 'Domain %s, %s Outages' % (self.small_id,
                                          sum(self.outage.values()))
        # significant(self.cost())


if __name__ == '__main__':
    import doctest
    doctest.testmod()
