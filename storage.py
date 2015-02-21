import numpy as np
from misc import significant

from devices import Device
from econ import Bid, Offer


class FLA(object):
    def __init__(self):
        """Flooded Lead Acid Battery Parameters :cite:`McManus2012`

        Attributes:
            usable: (float) Usable/Effective capacity (ratio).
            tox_kg: (float) Human Toxicity Factor (CTUh/kg).
            density: (float) energy density, (wh / kg).
            cost_kg: (float) cost of storage, (USD/kg).
            cost_kw: (float) depletion/usage cost per kw (USD/kw).

        """
        self.name = 'FLA'
        self.usable = .5
        self.co2_kg = 7.
        self.tox_kg = 8.
        self.density = 50.
        self.cost_kg = 4.5
        self.cost_kwh = .13


class IdealStorage(Device):
    """Ideal storage class.

    Note:
        This is an ideal, there are no self discharge or efficiency losses,
        peukert effect, charge rate adjustments or thermal adjustments.

    Attributes:
        throughput: (float) kWh into battery.
        surplus: (float) Wh excess energy.
        nominal_capacity: (float) in Wh.
        drained_hours: (float) hours empty.
    """
    def __init__(self, capacity, chemistry=None):
        """
        Args:
            capacity: (float) Wh.
            chemistry: (object) Battery Chemistry Parameters (default FLA).

        """
        if chemistry is None:
            self.chem = FLA()
        self.nominal_capacity = capacity
        self.classification = "storage"
        self.state = capacity  # start full
        self.throughput = 0.
        self.surplus = 0.
        self.drained_hours = 0.
        self.full_hours = 0.
        self.shortfall = 0.
        self.state_series = []
        self.hours = []
        self.timeseries = []  # todo: not currently used, needed for interp?
        self.loss_occurence = 0
        self.c_in = []
        self.c_out = []

    def tox(self):
        return self.weight()*self.chem.tox_kg

    def co2(self):
        return self.weight()*self.chem.co2_kg

    def weight(self):
        """Storage weight in kg."""
        return self.nominal_capacity/self.chem.usable/self.chem.density

    def cost(self):
        fixed = self.weight()*self.chem.cost_kg
        return fixed

    def capacity(self):
        return self.nominal_capacity

    def curtailment_ratio(self, record):
        """Ratio of energy that has a curtailment penalty."""
        return 0.

    def hasenergy(self, record):
        """Determine if a device has energy.
        """
        return self.state

    def needsenergy(self, record):
        """Determine if device needs energy.
        """
        return self.nominal_capacity - self.state

    capacity_availible = needsenergy

    def offer(self, record):
        """Energy offer.

        Returns:
            (Offer)

        """
        o = Offer(id(self), self.hasenergy(record), self.sell_kwh())
        o.storage = True
        return o

    def bid(self, record):
        b = Bid(id(self), self.needsenergy(record), self.buy_kwh())
        b.storage = True
        return b

    def droopable(self, record):
        return 1.

    def sell_kwh(self):
        """Cost of withdrawing energy."""
        return self.chem.cost_kwh

    def buy_kwh(self):
        """Value of storing energy."""
        # no value to store
        return 0.00001 #self.chem.cost_kwh

    def depletion(self):
        """Battery depletion expense.

        This is a simple calculation that levelizes battery replacement costs.

        .. math:: (\\text{kWh throughput}) \\cdot (\\text{kWh cost})

        Returns:
            (float) USD
        """
        prospective = self.throughput/1000.*self.chem.cost_kwh
        return prospective

    def power_io(self, power, record=None, hours=1.):
        """Power input/output

        >>> s = IdealStorage(100)
        >>> 10 + s
        -10.0

        >>> - 10 + s
        0.0

        Args:
            power: (float) watts positive charging, negative discharging.
            hours: (float) time delta (default 1 hour).

        Returns:
            energy: (float) watt hours constrained, +/- full/discharged.

            """
        energy = power*hours
        self.hours.append(hours)

        if energy > 0:
            # Track C rate
            self.c_in.append(energy/self.nominal_capacity)
            max_in = self.nominal_capacity - self.state
            e_delta = min(energy, max_in)
            self.state += e_delta
            if e_delta != energy:
                # energy has not all been stored
                surplus = energy - e_delta
                self.surplus += surplus
                active_time = surplus/energy * hours
                self.full_hours += hours - active_time
            self.throughput += e_delta

        if energy < 0:
            # Track C rate
            self.c_out.append(energy/self.nominal_capacity)
            max_out = self.state
            e_delta = - min(-energy, max_out)
            self.state += e_delta
            if e_delta != energy:
                # energy has not all been stored
                shortfall = max_out + energy
                self.shortfall += shortfall
                shortfall_time = shortfall/energy * hours
                self.drained_hours += shortfall_time
                active_time = hours - shortfall_time
                self.loss_occurence += 1

        if energy == 0:
            if self.state == 0:
                self.drained_hours += hours
            if self.state == self.nominal_capacity:
                self.full_hours += hours
            e_delta = 0

        self.state_series.append(self.soc())
        return e_delta - energy

    def autonomy(self):
        """ Autonomy C/median discharge rate

        This might be stupid, but median discharge rate is in watts,
        1 C discharge rate is in watt hours. So 1C over median discharge
        rate looks like the reciprocal.

        """
        median_c = np.median(self.c_out)
        return abs(1.0/median_c)

    def __radd__(self, x):
        return self.power_io(x)

    def soc(self):
        return self.state/self.nominal_capacity

    def details(self):
        soc_series = np.array(self.state_series)
        results = {
            'Storage shortfall (wh)': significant(self.shortfall),  # ENS
            'Storage surplus (wh)': significant(self.surplus),
            'Storage full (hours)': significant(self.full_hours),
            'Storage lolh (hours)': significant(self.drained_hours),
            'Storage throughput (wh)': significant(self.throughput),
            'Storage outages (n)': self.loss_occurence,
            'Storage mean soc (%)': round(soc_series.mean()*100, 1),
            'Storage median soc (%)': round(np.median(soc_series)*100, 1),
            'Storage Autonomy 1/C (hours)': significant(self.autonomy())}
        return results

    def __repr__(self):
        return '%s Wh %s' % (significant(self.nominal_capacity),
                             self.chem.name)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
