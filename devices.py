from solpy import irradiation
import numpy as np
from misc import significant, module_temp
import networkx as nx

class Device(object):
    """Device

    Parameters:
        children (list): list of children
        device_co2 (float): cumulative energy losses (Wh)
        device_tox (float): device_tox
        device_cost (float): device cost
        """
    def __init__(self, array_like):
        self.children = array_like
        self.device_cost = 1.
        self.device_tox = 1.
        self.device_co2 = 1.

    def co2(self):
        return [i.co2() for i in self.children] + self.device_co2

    def cost(self):
        # assume a fixed cost for charge controller
        return [i.co2() for i in self.children] + self.device_cost

    def tox(self):
        return self.array.tox() + self.device_tox

    def graph(self):
        G = nx.Graph()
        G.add_node(self)
        for i in self.shape:
            G.add_node(i)
            G.add_edge(self, i)
            G = nx.compose(G, i.graph())
        return G

    def __repr__(self):
        return 'Device'

    #def __getattr__(self, name):
    #    v = 0
    #    for i in self.children:
    #        if hasattr(i, name):
    #            v += getattr(i, name)()
    #    return v


class LA(object):
    def __init__(self):
        """ Flooded Lead Acid Battery Parameters

        Attributes:
            usable (float): Usable/Effective capacity (ratio)
            tox_kg (float): Human Toxicity Factor (CTUh/kg)
            density (float): energy density, (wh / kg)
            cost_kg (float): cost of storage, (USD/kg)
            cost_kw (float): depletion/usage cost per kw (USD/kw)

        """
        self.name = 'FLA'
        self.usable = .5
        self.co2_g = 7000.
        self.tox_kg = 8.
        self.density = 50.
        self.cost_kg = 4.5
        self.cost_kw = .13


class IdealStorage(object):
    """Ideal Storage class
    no self discharge
    no efficiency losses
    no peukert
    no charge rate adjustments
    no thermal adjustements
    """
    def __init__(self, capacity, chemistry=None):
        """
        Note:
            capacity is usable capacity in wh


        """
        if chemistry is None:
            self.chem = LA()
        self.capacity = capacity
        self.state = capacity  # start full
        self.throughput = 0.
        self.surplus = 0.
        self.drained_hours = 0.
        self.full_hours = 0.
        self.shortfall = 0.
        self.state_series = []
        self.in_use = 0.
        self.loss_occurence = 0
        self.c_in = []
        self.c_out = []
        self.r = 1.

    def rvalue(self):
        return self.r*self.loss_occurence

    def tox(self):
        return self.weight()*self.chem.tox_kg

    def co2(self):
        return self.weight()*self.chem.co2_g

    def weight(self):
        """weight in kg"""
        return self.capacity/self.chem.usable/self.chem.density

    def cost(self):
        fixed = self.weight()*self.chem.cost_kg
        return fixed

    def depletion(self):
        prospective = self.throughput/1000.*self.chem.cost_kw
        return prospective

    def power_io(self, power, hours=1.0):
        "power in watts"
        energy = power*hours
        self.in_use += hours

        if energy > 0:
            self.c_in.append(energy/self.capacity)
            max_in = self.capacity - self.state
            e_delta = min(energy, max_in)
            self.state += e_delta
            if e_delta != energy:
                surplus = energy - e_delta
                self.surplus += surplus
                active_time = surplus/energy * hours
                self.full_hours += active_time
            self.throughput += e_delta

        if energy < 0:
            self.c_out.append(energy/self.capacity)
            max_out = self.state
            e_delta = - min(-energy, max_out)
            self.state += e_delta
            if e_delta != energy:
                shortfall = max_out + energy
                self.shortfall += shortfall
                shortfall_time = shortfall/energy * hours
                self.drained_hours += shortfall_time
                active_time = hours - shortfall_time
                self.loss_occurence += 1

        if energy == 0:
            if self.state == 0:
                self.drained_hours += hours
            if self.state == self.capacity:
                self.full_hours += hours
            e_delta = 0

        self.state_series.append(self.soc())
        return e_delta - energy

    def autonomy(self):
        """ this might be stupid"""
        median_c = np.median(self.c_out)
        return abs(1.0/median_c)

    def __radd__(self, x):
        return self.power_io(x)

    def soc(self):
        return self.state/self.capacity

    def details(self):
        # print '#ELCC'
        # print '#LOLP'
        soc_series = np.array(self.state_series)
        results = {
            'shortfall (wh)': significant(self.shortfall),  # ENS
            'surplus (wh)': significant(self.surplus),
            'full (hours)': significant(self.full_hours),
            'lolh (hours)': significant(self.drained_hours),
            'throughput (wh)': significant(self.throughput),
            'loss occurence (n)': self.loss_occurence,
            'mean soc (%)': round(soc_series.mean()*100, 1),
            'median soc (%)': round(np.median(soc_series)*100, 1),
            'Autonomy 1/C (hours)': significant(self.autonomy())}
#        'storage cost (US)' : round(self.cost(),2),
#        'storage depletion (US)' : round(self.depletion(),2),
        return results

    def __repr__(self):
        return '%s Wh %s Battery' % (self.chem.name,
                                     significant(self.capacity))


class SystemSeed(object):
    def __init__(self):
        pass

    def scale(self):
        pass

    def interconnect(self):
        pass

    def frequency_reg(self):
        pass


class SimplePV():
    """Simple PV module (Generic)

    Parameters:
        vmp (float): voltage
        imp (float): current
        cost_watt (float): cost (USD/w)
        tc_vmp (float): voltage temperature coefficent (V/C)

    """
    def __init__(self, W):
        imax = 8.
        v_bus = [24, 20, 12]
        self.cost_watt = .8
        for v in v_bus:
            vmp = v*1.45
            imp = W/vmp
            if imp < imax:
                self.vmp = vmp
                self.imp = imp
        self.tc_vmp = self.vmp * -0.004

    def area(self):
        return self.nameplate()/1000./.2

    def co2(self):
        """CO2 for SystemSeed
        Note:
        Assuming 1500 kg/kw
        ~41g/kWh
        ~36500 hours of operation
        """
        return 1.5 * self.nameplate()/1000.

    def cost(self):
        """total module cost"""
        return self.nameplate() * self.cost_watt

    def nameplate(self):
        v, i = self.output(1000., 25.)
        W = v*i
        return W

    def output(self, irr, t_cell):
        """temperature compensated module output"""
        vmp = self.vmp - (25-t_cell) * self.tc_vmp
        return vmp, self.imp*irr/1000.

    def tox(self):
        return self.nameplate()*.3

    __call__ = output

    #def __call__(self, irr, t_cell=25):
    #    return self.output(irr, t_cell)

    def __repr__(self):
        v, i = self(1000., 25.)
        W = v*i
        return '%s W PV' % W


class ChargeController():
    """Ideal Charge Controller

    Parameters:
        loss (float): cumulative energy losses (Wh)
        array (object): PV Array
        cost (float): device cost

    """
    def __init__(self, array):
        self.loss = 0.
        self.array = array
        self.device_cost = 10.
        self.device_tox = 3.
        self.device_co2 = 5.

    def co2(self):
        """CO2 for SystemSeed
        Note:
        Assuming 1500 kg/kw
        ~41g/kWh
        ~36500 hours of operation
        """
        return self.array.co2() + self.device_co2

    def cost(self):
        # assume a fixed cost for charge controller
        return self.array.cost() + self.device_cost

    def graph(self):
        G = nx.Graph()
        G.add_node(self.array)
        G.add_node(self)
        G.add_edge(self,self.array)
        return G

    def losses(self):
        return self.loss

    def nameplate(self):
        v,i = self.array(1000., 25.)
        W = v*i
        return W

    def output(self, irr, t_cell):
        v, i = self.array(irr, t_cell)
        return v*i

    def tox(self):
        return self.array.tox() + self.device_tox

    __call__ = output

    def __repr__(self):
        return 'CC'

class MPPTChargeController(ChargeController):
    """MPPT Charge Controller

    Note: Assumes Linear efficiency curve

    Parameters:
        loss (float): cumulative energy losses (Wh)
        array (object): PV Array
        efficiency (float): energy conversion efficiency
        cost (float): device cost

    """
    def __init__(self, array, efficiency=.95):
        self.loss = 0.
        self.array = array
        self.efficiency = efficiency
        self.device_cost = 10.
        self.device_tox = 3.
        self.device_co2 = 5.

    def output(self, irr, t_cell):
        v, i = self.array(irr, t_cell)
        # i = irr/1000. * self.imp
        w = v*i
        self.loss += (1.-self.efficiency)*w
        return v*i*self.efficiency

    __call__ = output

    def __repr__(self):
        return 'MPPT CC %s %%' % significant(self.efficiency*100.)


class SimpleChargeController(ChargeController):
    def __init__(self, array, vnom=12.5):
        self.loss = 0
        self.array = array
        self.vnom = vnom
        self.device_tox = 3.
        self.device_co2 = 5.
        self.device_cost = 7.

    def output(self, irr, t_cell):
        v, i = self.array.output(irr, t_cell)
        # i = irr/1000. * self.imp
        self.loss += (v - self.vnom) * i
        return self.vnom * i

    __call__ = output

    def __repr__(self):
        return 'Simple CC Nom: %sV' % self.vnom


class PVSystem(object):
    def __init__(self, shape, place, tilt, azimuth):
        """PV System/Plant

        Parameters:
        place (lat,lon): geolocation
        tilt (degrees): array tilt
        azimuth (degrees): array azimuth
        shape (list): list of energy source objects
        life (years): expected life of system
        """
        self.place = place
        self.tilt = tilt
        self.azimuth = azimuth
        self.shape = shape
        self.life = 20.

    def p_dc(self, ins, t_cell=25):
        """dc power output"""
        total_dc = 0
        for i in self.shape:
            v, a = i.array.output(ins, t_cell)
            total_dc += v * a
        return total_dc

    def output(self, irr, t_cell):
        return sum([i.output(irr, t_cell) for i in self.shape])

    def area(self):
        return self.p_dc(1000.)/1000./.15

    def co2(self):
        # 41g/kWh
        # life ~36500 hours of operation
        # 1496500 g/kw
        return 1496500 * self.p_dc(1000.)/1000.

    def cost(self):
        return sum([i.cost() for i in self.shape])

    def depletion(self):
        """1 year depleation assuming lifetime"""
        return self.cost()/self.life

    def graph(self):
        G = nx.Graph()
        G.add_node(self)
        for i in self.shape:
            G.add_node(i)
            G.add_edge(self, i)
            G = nx.compose(G, i.graph())
        return G

    def losses(self):
        """total losses"""
        return sum([i.losses() for i in self.shape])

    def tox(self):
        """total Toxicity"""
        return sum([i.tox() for i in self.shape])

    def __call__(self, t):
        try:
            irr = irradiation.irradiation(t, self.place, t=self.tilt,
                                          array_azimuth=self.azimuth,
                                          model='p9')
            t_cell = module_temp(irr, t)
            return self.output(irr, t_cell)
        except Exception as e:
            print e
            return 0

    def __repr__(self):
        return 'Plant %s, %s' % (significant(self.place[0]),
                                 significant(self.place[1]))


class Domain(object):
    def __init__(self, load=None, storage=None, gen=None, name='A'):
        self.load = load
        self.gen = gen
        self.storage = storage
        self.g = []
        self.l = []
        self.d = []
        self.net_g = []  # used generation
        self.net_l = []  # enabled load
        self.surplus = 0
        self.shortfall = 0
        self.name = name

    def autonomy(self):
        """this is a hack assumes hour time intervals"""
        # g_ave = sum(self.g)/len(self.g)
        l_med = np.median(self.l)
        return self.storage.capacity/l_med  # hours

    def eta(self):
        return sum(self.net_l)/(sum(self.g)+self.gen.losses())

    def capacity_factor(self):
        if self.gen:
            return sum(self.net_l)/(self.gen.p_dc(1000.)*24*365)
        else:
            return 0.

    def details(self):
        results = {
            'gen losses (wh)': significant(self.gen.losses()),
            'desired load (wh)': significant(sum(self.l)),
            'Autonomy (hours) (Median Load/C)': significant(self.autonomy()),
            'Capacity Factor (%)': significant(self.capacity_factor()*100.),
            'Domain Parts (USD)': significant(self.cost),
            'Domain depletion (USD)': significant(self.depletion),
            'A (m2)': significant(self.area),
            'Tox (CTUh)': significant(self.tox),
            'CO2 (gCO2 eq)': significant(self.co2),
            'eta T (%)': significant(self.eta()*100)
        }
        if self.gen:
            results['STC (w)'] = significant(self.gen.p_dc(1000.))
        if self.storage:
            results['capacity (wh)'] = significant(self.storage.capacity)
        return results

    def graph(self):
        G = nx.Graph()
        G.add_node(self)
        if self.gen:
            G.add_node(self.gen)
            G.add_edge(self, self.gen)
            G = nx.compose(G, self.gen.graph())
        if self.load:
            G.add_node(self.load)
            G.add_edge(self, self.load)
        if self.storage:
            G.add_node(self.storage)
            G.add_edge(self, self.storage)
        return G

    def STC(self):
        if self.gen:
            return self.gen.p_dc(1000.)
        else:
            return 0.

    def __call__(self, record):
        if self.load:
            l_t = self.load(record['datetime'])
        else:
            l_t = 0

        if self.gen:
            g_t = self.gen(record)
        else:
            g_t = 0

        self.g.append(g_t)
        self.l.append(l_t)

        d = 0
        if self.storage:
            d = g_t - l_t + self.storage
            self.d.append(d)
            # todo: i don't like this accounting its currently being tracked
            # in storage.
            # usable_g = g - surplus
            # net_l = l - shortfall
            self.net_l.append(min(l_t - d, l_t))
            # enabled_load = l_t or 0
            return d
        else:
            d = g_t - l_t
            # todo: assumes full hour, might not be correct
            self.net_l.append(max(0., l_t))
            self.net_g.append(max(0., l_t))
            self.surplus += max(0., d)
            if d < 0:
                self.shortfall += l_t
            return d

    def __repr__(self):
        return 'Domain $%s' % significant(self.cost)

    def __getattr__(self, name):
        v = 0
        for i in [self.gen, self.load, self.storage]:
            if hasattr(i, name):
                v += getattr(i, name)()
        return v

class AdaptiveConsumer(object):
    def __init__(self):
        pass


class LoadShedRelay(object):
    def __init__(self):
        pass
