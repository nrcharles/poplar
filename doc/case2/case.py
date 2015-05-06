"""Single reliablity domain with discrete loads."""
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

plane = InclinedPlane(Site(PLACE), 28.1, 180.)
plant = MPPTChargeController([SimplePV(118, plane)])
fan = loads.FanLoad(15)
fan.per_key = 0.07
lights = loads.LightingLoad(3*4)
lights.per_kwh = .10

tv = loads.tv(20)
tv.per_kwh = 0.08
batt = IdealStorage(400.)

case = Gateway([lights,
               tv,
               fan,
               plant,
               batt])

for i, r in enumerate(eere.EPWdata('418830')):
    env.update_time(r['datetime'])
    case()

if __name__ == '__main__':
    print case.details()
    from poplar.visuals import rst_domain, rst_batt, rst_graph
    foo = open('case.rst', 'w')
    title = 'Graph of system with discrete loads'
    foo.writelines(rst_graph(case, title))

    title = 'System with discrete loads'
    foo.writelines(rst_domain(case, title))

    title = 'System with discrete loads'
    foo.writelines(rst_batt(batt, title))

    foo.close()
