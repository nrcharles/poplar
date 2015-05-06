"""System with MPPT Charge Controller sized for best STEEP merit."""
import sys
sys.path.insert(0, '../../')
import logging
from caelum import eere
import poplar.environment as env
env.set_weather(eere.EPWdata('418830'))
logging.basicConfig(level=logging.WARNING)

from poplar.devices import Gateway
from poplar.storage import IdealStorage
from poplar.sources import SimplePV, Site, InclinedPlane
from poplar.controllers import MPPTChargeController
import poplar.loads as loads
PLACE = (24.811468, 89.334329)

# Alternate sizings
# Battery (Wh)   PV (Wp)
# ==========================
# 207.29314482,   97.12266251
# 176.08863086,  100.84768585
# 178.0,         100.0

batt = IdealStorage(176.1)
plane = InclinedPlane(Site(PLACE), 28.1, 180.)
plant = MPPTChargeController([SimplePV(100.9, plane)])
case = Gateway([loads.Annual(),
               plant,
               batt])

for i, r in enumerate(eere.EPWdata('418830')):
    env.update_time(r['datetime'])
    case()

if __name__ == '__main__':
    print case.details()
    from poplar.visuals import rst_domain, rst_batt, rst_graph
    title = 'System with MPPT Charge Controller sized for best STEEP merit'
    rst_graph(case, title)
    foo = open('case.rst', 'w')

    foo.writelines(rst_domain(case, title))
    foo.writelines(rst_batt(batt, title))
    foo.close()
