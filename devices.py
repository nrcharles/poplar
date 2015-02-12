from solpy import irradiation
import numpy as np
from misc import significant, module_temp
import networkx as nx


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


class SimplePV(Device):

    """Simple PV module (Generic).

    Attributes:
        imp: (float) current.
        cost_watt: (float) cost (USD/w).
        tc_vmp: (float) voltage temperature coefficent (V/C).
        tc_imp: (float) current temperature coefficent (V/C).

    Note: Constants choosen based on typical manufacturer data

    """

    def __init__(self, W):
        """Create a generic PV module typical of a module in that power class.

        Args:
            W (float): Watts
        """
        imax = 8.
        v_bus = [24, 20, 12]
        self.cost_watt = .8
        for v in v_bus:
            vmp = v*1.35
            imp = W/vmp
            if imp < imax:
                self.vmp = vmp
                self.imp = imp
        self.tc_vmp = self.vmp * -0.0044
        self.tc_imp = self.imp * 0.0004

    def area(self):
        """Total area PV Module in M^2."""
        return self.nameplate()/1000./.15

    def co2(self):
        """CO2 for system.

        Note:
        Assuming 1800 kg/kWp
        ~1600-2000/kWp :cite:`laleman2013comparing`

        Returns:
            (float): kg CO2 eq
        """
        return 1.8 * self.nameplate()

    def cost(self):
        """total module cost."""
        return self.nameplate() * self.cost_watt

    def nameplate(self):
        """Nameplate rating at STC conditions."""
        v, i = self.output(1000., 25.)
        W = v*i
        return W

    def output(self, irr, t_cell):
        """Temperature compensated module output.

        Note: this is a heuristic method.


        This is often calulated either by :cite:`DeSoto2006`, :cite:`King2007`
        or :cite:`Dobos2012`.

        For computer processing performance temperature compensation is
        simplified to:

        .. math:: V_{mp} = V_{mpo} + \\beta_{Vmp}(T_{c} - T_{o})

        >>> pv = SimplePV(133.4)
        >>> v, i = pv(1000, 25.)
        >>> round(v*i, 1)  # NIST: 133.4
        133.4

        >>> v, i = pv(882.6, 39.5)
        >>> round(v*i, 1)  # NIST 109.5
        110.2

        >>> v, i = pv(696.0, 47.0)
        >>> round(v*i, 1)  # NIST 80.1 i+
        83.9

        >>> v, i = pv(465.7, 32.2)
        >>> round(v*i, 1) # NIST 62.7
        60.2

        >>> v, i = pv(189.9, 36.5)
        >>> round(v*i, 1)  # NIST 23.8
        24.1

        Args:
            irr: (float) W/m^2 irradiance or Wh/mh insolation.
            t_cell: (float) temperature of cell in C.

        Returns:
            vmp, imp: (tuple) of voltage and current.
        """
        vmp = self.vmp + (t_cell - 25.) * self.tc_vmp

        return vmp, self.imp * irr / 1000.

    def tox(self):
        """Module Toxicity.

        This is not a well developed area.
        """
        return self.nameplate() * .3  # todo: placeholder value

    __call__ = output

    def __repr__(self):
        v, i = self(1000., 25.)
        W = v*i
        return '%s W PV' % significant(W)


class PVSystem(Device):

    """
    PV System/Plant.

    Attributes:
        place: (tuple): lat,lon geolocation.
        tilt: (float) degrees array tilt.
        azimuth: (float) degrees array azimuth.
        shape: (list) of energy source objects
        life: (int) years expected life of system

    """

    def __init__(self, children, place, tilt, azimuth):
        """Should have at least one child.

        Args:
            children(list): list of power conversion devices.
            place(tuple): lat, lon geolocation.
            tilt(float): array tilt in degrees.
            azimuth(degrees): array azimuth in degrees.

        """
        self.place = place
        self.classification = "source"
        self.dispactachable = False
        self.tilt = tilt
        self.azimuth = azimuth
        self.children = children
        self.device_cost = 0.
        self.device_co2 = 0.
        self.device_tox = 0.
        self.life = 20.
        self.gen = True

    def nameplate(self):
        """Sum of STC DC nameplate power."""
        total_dc = 0
        for i in self.children:
            total_dc += i.nameplate()
        return total_dc

    def output(self, irr, t_cell):
        """Sum of energy output."""
        return sum([i.output(irr, t_cell) for i in self.children])

    def depletion(self):
        """1 year depletion."""
        return self.cost()/self.life

    def losses(self):
        """Sum total losses."""
        return sum([i.losses() for i in self.children])

    def tox(self):
        """Sum total Toxicity."""
        return sum([i.tox() for i in self.children])

    def energy(self, t):
        """Calculate total energy for a time period.

        Args:
            t(dict): weather data record
        """
        try:
            irr = irradiation.irradiation(t, self.place, t=self.tilt,
                                          array_azimuth=self.azimuth,
                                          model='p9')
            t_cell = module_temp(irr, t)
            return self.output(irr, t_cell)
        except Exception as e:
            print(e)
            return 0

    __call__ = energy

    def __repr__(self):
        return 'Plant %s, %s' % (significant(self.tilt),
                                 significant(self.azimuth))


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
        self.lolh = 0.
        self.r = 1.

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
            'Domain surplus (kWh)': significant(self.surplus),
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
            if child.classification == "source":
                nameplate += child.nameplate()
        return nameplate

    def weather_series(self, array_like):
        for i in array_like:
            self(i)

    def energy_source(self):
        """Find cheapest energy source.

        hasenergy and sell_kwh makes up an offer.

        Returns:
            (object): Device or Domain to cover energy shortfall.
        """
        min_kwh_c = 10
        choice = None
        # select lowest energy source bid
        for child in self.children:
            if child.classification == 'storage':
                if child.hasenergy() and child.sell_kwh() < min_kwh_c:
                    choice = child
                    min_kwh_c = child.chem.cost_kwh
        return choice

    def energy_sink(self):
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
            if child.classification == 'storage':
                if child.needsenergy() and child.buy_kwh() > min_kwh_c:
                    choice = child
                    min_kwh_c = child.chem.cost_kwh
        return choice

    def bank(self, energy):
        """Bank energy."""
        if energy > 0:
            net = self.deposit(energy)
        if energy < 0:
            net = self.withdraw(energy)
        return net

    def deposit(self, energy):
        """Store surplus energy in a domain.

        Args:
            energy_surplus: (float) positive in (wH)

        Returns:
            (float): (wH) surplus that couldn't be transferred.
        """
        # energy is surplus (positive)
        storage = self.energy_sink()
        while storage and energy > 0:
            a = storage.needsenergy()
            delta = min(a, energy)
            storage.power_io(delta)
            energy -= delta
            storage = self.energy_sink()

        return energy

    def withdraw(self, energy):
        """Withdraw energy from a domain to cover a shortfall.

        Args:
            energy_shortfall(float): negative, energy (wH) needed.

        Returns:
            (float): wH shortfall that couldn't be covered.
        """
        # energy is shortfall (negative)
        storage = self.energy_source()
        while storage and energy < 0:
            a = storage.state
            delta = min(a, abs(energy))
            storage.power_io(-delta)
            energy += delta
            storage = self.energy_source()

        return energy

    def power_io(self, record, hours=1.0):
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
        self.time_series.append(record['datetime'])

        # calculate energy demand
        demand = 0
        for child in self.children:
            if child.classification == 'load':
                demand += child(record['datetime'])

        # todo: demand response
        # deferable_capacity = 0
        # dimmable_capacity = 0
        source = 0
        for child in self.children:
            if child.classification == 'source':
                source += child(record)

        # reconcile energy shortages
        delta = source - demand
        self.g.append(source)
        self.l.append(demand)

        net = self.bank(delta)

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
            if child.classification == 'storage':
                energy_stored += child.state
                nominal_capacity += child.nominal_capacity

        state = energy_stored/nominal_capacity
        self.state_series.append(state)

        return net

    def depletion(self):
        return self.parameter('depletion')

    def rvalue(self):
        return self.r*self.outages

    __call__ = power_io

    def __repr__(self):
        return 'Domain $%s' % significant(self.cost())


if __name__ == '__main__':
    import doctest
    doctest.testmod()
