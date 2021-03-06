import numpy as np
import networkx as nx
import environment as env
from misc import significant, Counter
from econ import low_offer, rank_bids
from visuals import multi_report
from merit import STEEPMerit

import logging
logger = logging.getLogger(__name__)

SMALL_ID = Counter()


class Model(object):
    """Base object class."""
    def graph(self):
        """Device Graph of all decendants.

        Returns:
            (Graph)
        """

        # todo: this code could use some polishing

        if not hasattr(self, 'network'):
            # find an existing network graph
            if hasattr(self, 'children'):
                for i in self.children:
                    self.network = i.graph()
                    self.network.add_node(self)
                    self.network.add_edge(self, i)
                    break
            else:
                self.network = nx.Graph()
                self.network.add_node(self)

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

    def find_node(self, obj_id):
        for node in self.network:
            if id(node) == obj_id:
                return node
        for i in self.network:
            print('%s,%s' % (i, id(i)))

        raise KeyError('Node %s not found' % obj_id)

    def path(self, node):
        """Shortest path to node."""
        return nx.shortest_path(self.network, self, node)


class Device(Model):

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
        # todo: should I put these device attributes in a dict.
        self.device_cost = 0.
        self.device_tox = 0.
        self.device_co2 = 0.
        self.device_area = 0.
        self.name = 'Device'

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

    def connected_domains(self):
        # isdomain = lambda x: (type(x) is Domain) and (x is not self)
        isdomain = lambda x: (type(x) is Gateway)
        return filter(isdomain, self.network)

    def dest_gateway(self, obj_id):
        """find dest obj_id's input gateway

        Returns:
            Gateway
        """

        node = self.find_node(obj_id)
        for step in reversed(self.path(node)):
            if type(step) is Gateway:
                return step
        print 'dest', obj_id, 'self', id(self)
        print self.path(node)
        raise KeyError('Gateway for %s not found' % obj_id)

    def src_gateway(self, obj_id):
        """find output gateway from self to dest obj_id

        Returns:
            Gateway
        """
        node = self.find_node(obj_id)
        for step in self.path(node):
            if type(step) is Gateway:
                return step
        print obj_id, id(self)
        print self.path(node)
        raise KeyError('Gateway for %s not found' % obj_id)

    def __repr__(self):
        return self.name


class Gateway(Device):

    """Base Gateway Class.

    Attributes:
        g: (list) total gen delivered to domain.
        l: (list) desired load.
        d: (list) delta energy; surplus or shortfall.
        children: (list) devices in domain.
        net_l: (list) enabled load (Wh).
        loss_occurence: (int) loss (Wh).
        shortfall: (float) total energy shortfall (Wh).
    """

    def __init__(self, children=None, merit=None):
        """Should have at least one child but should probably have two.

        Args:
            children (list): loads, storage, and generation
        """
        super(Gateway, self).__init__()
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
        self.shortfall = 0.
        self.domain_r = 1.
        self.credits = {}
        self.debits = {}
        self.balance = {}
        self.demand = {}
        self.outage = {}
        self.source = {}
        self.lolh = 0.
        self.network = self.graph()
        self.export_power = True
        if merit is None:
            self.system_merit = STEEPMerit()
        else:
            self.system_merit = merit

    def autonomy(self):
        """Calculate domain autonomy.

        Returns:
            (float) hours

        Note: assumes hour time intervals

        """
        # g_ave = sum(self.g)/len(self.g)
        # todo: this could be improved
        net_l = 0.

        for node in self.network.neighbors(self):
            if hasattr(node, 'dmnd') and type(node) is not Gateway:
                # net_l += np.median(node.dmnd.values())
                net_l += abs(np.mean(node.dmnd.values()))
        return self.domain_capacity() / net_l

    def max_load(self, intervals=48):
        demand = self.log_dict_to_list('demand')
        l_max = min([sum(demand[i:i+intervals]) for i in range(len(demand)-intervals)])
        return l_max

    def domain_capacity(self):
        capacity = 0
        for node in self.network.neighbors(self):
            if hasattr(node, 'nominal_capacity'):
                capacity += node.nominal_capacity
        return capacity

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

    def total_capacity(self):
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
        return [getattr(self, log_dict).setdefault(i, default)
                for i in self.time_series]

    def details(self):
        """Create dict of metrics."""
        results = {
            'Demand (Wh)': significant(sum(self.log_dict_to_list('demand'))),
            'Net (Wh)': significant(sum(self.log_dict_to_list('balance'))),
            'Domain sources (Wh)':
                significant(sum(self.log_dict_to_list('source'))),
            'Domain credits (Wh)':
                significant(sum(self.log_dict_to_list('credits'))),
            'Domain debits (Wh)':
                significant(sum(self.log_dict_to_list('debits'))),
            'Domain Generation losses (Wh)':
            significant(self.parameter('losses')),
            'Autonomy (hours) (mean load/C)': significant(self.autonomy()),
            '%s hour max load' % 48: significant(self.max_load(48)),
            # 'Capacity Factor (%)': significant(self.capacity_factor()*100.),
            'Domain surplus (Wh)': significant(self.surplus()),
            # 'Domain Generation (Wh)': significant(sum(self.g)),
            'Domain Parts (USD)': significant(self.cost()),
            'Domain depletion (USD)': significant(self.depletion()),
            'Domain LOLH (hours)': significant(self.lolh),
            'Domain outages (n)': significant(sum(self.outage.values())),
            'Domain shortfall (Wh)': significant(self.shortfall),
            'A (m2)': significant(self.parameter('area')),
            # 'Toxicity (CTUh)': significant(self.tox()),
            'CO2 (kgCO2 eq)': significant(self.co2()),
            'Domain Efficiency (%)': significant(self.eta()*100),
            '%s' % str(self.system_merit): significant(self.merit()),
            'STC (W)': self.STC()
        }
        return results

    def merit(self):

        return self.system_merit(self)

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
            if type(child) == Gateway:
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
        source.power_io(-delta)
        source_domain = self.dest_gateway(offer.obj_id)
        source_domain.debits[key] -= delta
        source_domain.balance[key] -= delta
        logger.info('%s: Transfered %s Wh from %s toward %s Wh in %s',
                    key, delta, source, bid.wh, dest)
        return True

    def get_energy(self, bid):
        # energy auction
        key = env.time
        node = self.find_node(bid.obj_id)
        # initial_demand = node.needsenergy()
        initial_demand = self.demand[key]
        logger.debug("New auction %s for %s Wh", key, initial_demand)
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
            # self.lolh += self.timestep - (initial_demand-node.needsenergy())\
            self.lolh += self.timestep - (initial_demand - self.demand[key]) \
                / initial_demand * self.timestep
            return False
        return True

    def calc(self, hours=1.0):
        """Calculate energy.

        Gateways behave like an energy market, excess energy is are transfered
        to the device with the highest bid and energy shortfalls are covered
        from the device with the lowest offer.

        Args:
            hours (float):

        Returns:
            (float): net energy surplus or shortfall (Wh).

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
            if hasattr(i, 'needsenergy') and type(i) is not Gateway:
                e += i.needsenergy()
        return e

    def hasenergy(self):
        e = 0
        for i in self.children:
            if hasattr(i, 'hasenergy') and type(i) is not Gateway:
                e += i.hasenergy()
        return e

    def droopable(self):
        # todo: test this code
        e = 0.
        d = 0.
        for i in self.children:
            if hasattr(i, 'needsenergy') and type(i) is not Gateway:
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
            if hasattr(i, 'hasenergy') and type(i) is not Gateway:
                ce = i.hasenergy()
                cc = i.curtailment_ratio()
                c += ce*cc
                e += ce
        if e:
            # print c/e
            return c/e
        else:
            return 0.

    def surplus(self):
        g = 0
        for i in self.network.neighbors(self):
            if hasattr(i, 'generation') and type(i) is not Gateway:
                g += sum(i.balance.values())
        return g

    def depletion(self):
        return self.parameter('depletion')

    def rvalue(self):
        r = 0
        for i in self.network:
            if type(i) is Gateway:
                r += i.shortfall*i.domain_r
        return r

    __call__ = calc

    def __repr__(self):
        return 'Domain %s, %s Outages' % (self.small_id,
                                          sum(self.outage.values()))
        # significant(self.cost())


if __name__ == '__main__':
    import doctest
    doctest.testmod()
