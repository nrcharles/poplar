"""System with MPPT Charge Controller sized 48 hours autonomy."""

import sys
sys.path.insert(0, '../../')
import logging
from caelum import eere
import poplar.environment as env
env.set_weather(eere.EPWdata('418830'))
# logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.WARNING)

from poplar.devices import Gateway
from poplar.storage import IdealStorage
from poplar.sources import SimplePV, Site, InclinedPlane
from poplar.controllers import MPPTChargeController
import poplar.loads as loads
PLACE = (24.811468, 89.334329)

batt = IdealStorage(391.)
plane = InclinedPlane(Site(PLACE), 28.1, 180.)
plant = MPPTChargeController([SimplePV(75., plane)])
case = Gateway([loads.Annual(),
               plant,
               batt])

for i, r in enumerate(eere.EPWdata('418830')):
    env.update_time(r['datetime'])
    case()

if __name__ == '__main__':
    from poplar.visuals import rst_domain, rst_batt, rst_graph
    title = 'System with MPPT Charge Controller sized 48 hours autonomy'
    foo = open('case.rst', 'w')

    foo.writelines(rst_graph(case, title))
    foo.writelines(rst_domain(case, title))
    foo.writelines(rst_batt(batt, title))
    foo.close()
