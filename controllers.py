from misc import significant
from devices import Device


class ChargeController(Device):
    """Ideal Charge Controller

    Attributes:
        loss (float): cumulative energy losses (Wh).
        array (object): PV Array.
        cost (float): device cost.

    """
    def __init__(self, array_like):
        self.children = array_like
        self.device_cost = 10.
        self.device_tox = 3.  # todo: placeholder value
        self.device_co2 = 5.  # todo: placeholder value

    def losses(self):
        return self.loss

    def nameplate(self):
        return sum([i.nameplate() for i in self.children])

    def output(self, irr, t_cell):
        """Output of Ideal charge controller.

        Args:
            irr (float): irradiance W/m^2 or irradiation in Wh/m^2.
            t_cell (float): temperature of cell in C.

        Returns:
            (float): W or Wh depending on input units

        Note: Assumes that all modules are similar voltages.

        """
        w = 0.
        for child in self.children:
            v, i = child(irr, t_cell)
            w += v * i
        return w

    __call__ = output

    def __repr__(self):
        return 'CC'


class MPPTChargeController(ChargeController):
    """MPPT Charge Controller

    Attributes:
        loss: (float) cumulative energy losses (Wh).
        array: (object) PV Array.
        efficiency: (float) energy conversion efficiency.
        cost: (float) device cost.

    Note: Assumes Linear efficiency curve

    """
    def __init__(self, array_like, efficiency=.95):
        """
        Args:
            children: (array_like) PV array.
            efficiency: (float) energy conversion efficiency.
        """
        self.loss = 0.
        self.children = array_like
        self.efficiency = efficiency
        self.device_cost = 10.
        self.device_tox = 3.
        self.device_co2 = 5.

    def output(self, irr, t_cell):
        """Output of MPPT charge controller

        Args:
            irr (float): irradiance W/m^2 or irradiation in Wh/m^2.
            t_cell (float): temperature of cell in C.

        Returns:
            (float): W or Wh depending on input units.

        Assumes that all modules are similar voltages and that the efficiency
        curve is linear.

        .. math:: output = input \\cdot \\eta

        .. math:: losses = input \\cdot (1 -\\eta)

        """
        w = 0.
        for child in self.children:
            v, i = child(irr, t_cell)
            w += v * i
            self.loss += (1. - self.efficiency) * v * i
        return w * self.efficiency

    __call__ = output

    def __repr__(self):
        return '%s%% MPPT CC' % significant(self.efficiency*100.)


class SimpleChargeController(ChargeController):
    """Simple Charge Controller

    Attributes:
        loss: (float) cumulative energy losses (Wh).
        children: (object) PV Array.
        cost: (float) device cost.

    Note: Assumes output clipped to bus voltage vnom

    """
    def __init__(self, children, vnom=12.5):
        """
        Args:
            children: (array_like) PV array.
            vnom: (float) nominal bus voltage in (Volts) default 12.5.
        """
        self.loss = 0
        self.children = children
        self.vnom = vnom
        self.device_cost = 7.
        self.device_tox = 3.
        self.device_co2 = 5.

    def output(self, irr, t_cell):
        """Output of Simple charge controller.

        Args:
            irr (float): irradiance (W/m^2) or irradiation in (Wh/m^2)
            t_cell (float): temperature of cell in (C)

        Returns:
            (float): (W) or (Wh) depending on input units

        .. math:: output = V_{nom} \\cdot i

        .. math:: losses = (V_{module} - V_{nom}) \\cdot i

        """
        w = 0.
        for child in self.children:
            v, i = child(irr, t_cell)
            self.loss += (v - self.vnom) * i
            w += self.vnom * i
        return w

    __call__ = output

    def __repr__(self):
        return 'Simple CC Nom: %sV' % self.vnom


if __name__ == '__main__':
    import doctest
    doctest.testmod()
