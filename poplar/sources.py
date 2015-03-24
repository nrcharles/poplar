import environment as env
import logging
from devices import Device, Model
from solpy import irradiation
from misc import significant, module_temp
from econ import Offer

logger = logging.getLogger(__name__)

class Source(Device):
    def offer(self, dest_id):
        e = self.hasenergy()
        if e:
            return Offer(id(self), e, self.sell_kwh())
        else:
            return None

    def curtailment_ratio(self):
        """Ratio of energy that has a curtailment penalty."""
        return 1.0

    def energy(self):
        if not env.time in self.balance:
            output = self.output()
            self.balance[env.time] = output
            self.generation[env.time] = output
        return self.balance[env.time]


    def sell_kwh(self):
        # PV has curtailment penalty for unused energy
        return 0.

    def hasenergy(self):
        #key = record['datetime']
        #if not key in self.balance:
        #self.balance[key] = self.balance.setdefault(key,  self.energy(record))
        # return self.balance[key]
        return self.energy()

    def needsenergy(self):
        # stupid
        return 0.

    def droopable(self):
        # stupid
        return 0.

    def buyenergy(self):
        # stupid 
        return 0.

    def power_io(self, energy):
        key = env.time
        if abs(energy) > self.balance[key]:
            raise Exception('PV over commited')
        self.balance[key] += energy
        self.debits[key] = self.debits.setdefault(key, 0) + energy
        return 0.

    def total_gen(self):
        return sum(self.generation.values())
        #return sum(self.balance.values()) - sum(self.debits.values()) + self.losses()

class SimplePV(Device):

    """Simple PV module (Generic).

    Attributes:
        imp: (float) current.
        cost_watt: (float) cost (USD/w).
        tc_vmp: (float) voltage temperature coefficent (V/C).
        tc_imp: (float) current temperature coefficent (V/C).

    Note: Constants choosen based on typical manufacturer data

    """

    def __init__(self, W, irr_object):
        """Create a generic PV module typical of a module in that power class.

        Args:
            W (float): Watts
        """
        imax = 8.
        v_bus = [24, 20, 12]
        self.cost_watt = .8
        self.stc = W
        self.irr_object = irr_object
        self.children = [self.irr_object]
        # this is to handle optimizers putting in stupidly large numbers
        self.imp = imax
        self.vmp = W/imax
        for v in v_bus:
            vmp = v*1.35
            imp = W/vmp
            if imp < imax:
                self.vmp = vmp
                self.imp = imp
        if self.vmp > 800.:
            logger.warning('Module is stupidly large %s W',self.stc)

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
        return self.stc

    def output(self):
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
        key = env.time
        irr = self.irr_object()
        t_cell = module_temp(irr, env.weather[key])

        vmp = self.vmp + (t_cell - 25.) * self.tc_vmp

        return vmp, self.imp * irr / 1000.

    def tox(self):
        """Module Toxicity.

        This is not a well developed area.
        """
        return self.nameplate() * .3  # todo: placeholder value

    def depletion(self):
        """1 year depletion."""
        return self.cost()/self.life

    __call__ = output

    def __repr__(self):
        return '%s W PV' % significant(self.stc)


class Site(Model):

    """

    Attributes:
        place: (tuple): lat,lon geolocation.

    """

    def __init__(self, place):
        """Should have at least one child.

        Note that shading is not currently implimented, but this would
        where the code should probably go.

        Args:
            place (tuple): lat, lon geolocation.

        """
        self.place = place
        self.shading = None

    def output(self):
        return env.weather[env.time]

    __call__ = output

    def __repr__(self):
        return 'Site %s, %s' % (significant(self.place[0]),
                                 significant(self.place[1]))



class InclinedPlane(Device):

    """

    Attributes:
        tilt: (float) degrees array tilt.
        azimuth: (float) degrees array azimuth.
        solar_resource: (object)

    """

    def __init__(self, site, tilt, azimuth):
        """Should have at least one child.

        Args:
            weather: (object)
            tilt: (float) degrees array tilt.
            azimuth: (float) degrees array azimuth.

        """
        self.site = site
        self.tilt = tilt
        self.azimuth = azimuth
        self.children = [self.site]
        self.irr = {}

    def energy(self):
        """Calculate total energy for a time period.

        Args:
            key (dict value):
        """

        try:
            key = env.time
            if not key in self.irr:
                irr = irradiation.irradiation(self.site(),
                                              self.site.place,
                                              t=self.tilt,
                                              array_azimuth=self.azimuth,
                                              model='p9')
                self.irr[key] = irr
            return self.irr[key]
        except Exception as e:
            print(e)
            return 0

    __call__ = energy

    def __repr__(self):
        return 'Inclined Plane %s, %s' % (significant(self.tilt),
                                 significant(self.azimuth))


