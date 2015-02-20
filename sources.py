from devices import Device
from solpy import irradiation
from misc import significant, module_temp
from econ import Offer

class Source(Device):
    def offer(self, record):
        return Offer(id(self), self.hasenergy(record), self.sell_kwh())

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


class PVSystem(Source):

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
        self.balance = {}
        self.debits = {}

    def curtailment_ratio(self, record):
        """Ratio of energy that has a curtailment penalty."""
        return 1.0

    def nameplate(self):
        """Sum of STC DC nameplate power."""
        total_dc = 0
        for i in self.children:
            total_dc += i.nameplate()
        return total_dc

    def sell_kwh(self):
        # PV has curtailment penalty for unused energy
        return 0.

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

    def hasenergy(self, record):
        key = record['datetime']
        self.balance[key] = self.balance.setdefault(key,  self.energy(record))
        return self.balance[key]

    def needsenergy(self, record):
        # stupid
        return 0.

    def droopable(self, record):
        # stupid
        return 0.

    def buyenergy(self, record):
        # stupid 
        return 0.

    def power_io(self, energy, record):
        key = record['datetime']
        if abs(energy) > self.balance[key]:
            raise Exception('PV over commited')
        self.balance[key] += energy
        self.debits[key] = self.debits.setdefault(key, 0) + energy
        return 0.

    def __repr__(self):
        return 'Plant %s, %s' % (significant(self.tilt),
                                 significant(self.azimuth))


