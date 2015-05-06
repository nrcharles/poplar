"""System with multiple reliablity domains."""
import sys
import logging
from caelum import eere
sys.path.insert(0, '../../')
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


def system():
    """System definiton."""
    plane = InclinedPlane(Site(PLACE), 28.1, 180.)
    plant = MPPTChargeController([SimplePV(111.10, plane)], .87)

    fan = loads.FanLoad(15)
    fan.per_kwh = 0.07

    lights = loads.LightingLoad(3*4)
    lights.per_kwh = .10
    lightbatt = IdealStorage(131)
    lightbatt.buy = 0.095
    lightdom = Gateway([lights, lightbatt])
    lightdom.device_cost = 5.0
    lightdom.device_co2 = 10.0
    lightdom.export(False)

    tv = loads.tv(20)
    tv.per_kwh = 0.08
    batt = IdealStorage(48.91)
    tvbatt = IdealStorage(81.)
    tvbatt.buy = 0.075
    tvdom = Gateway([tv, tvbatt])
    tvdom.export(False)
    tvdom.device_cost = 5.0
    tvdom.device_co2 = 10.0

    case = Gateway([lightdom,
                    tvdom,
                    fan,
                    plant,
                    batt])

    case.domain_r = .005
    case.device_co2 = 10.

    return case

case = system()

nontrivial = []
for neighbor in case.network.neighbors(case):
    nontrivial.append(str(neighbor))

print nontrivial

for i, r in enumerate(eere.EPWdata('418830')):
    env.update_time(r['datetime'])
    case()

if __name__ == '__main__':
    print(case.details())
    from poplar.visuals import rst_domain, rst_batt, rst_graph
    foo = open('case.rst', 'w')
    title = 'Graph of system with multiple domains'
    foo.writelines(rst_graph(case, title))

    for node in case.network:
        subdomains = 0
        devices = 0
        for neighbor in node.network.neighbors(node):
            if type(neighbor) is Gateway:
                subdomains += 1
            else:
                devices += 1

        title = ""
        if subdomains > 0:
            title = 'Domain of %s sub domains and %s devices' % \
                (subdomains, devices)
        else:
            title = 'Domain of %s devices' % (devices)

        if type(node) is Gateway:
            foo.writelines(rst_domain(node, title))

        if type(node) is IdealStorage:
            foo.writelines(rst_batt(node, title))

    # title = 'Lighting domain in system with multiple domains'
    # foo.writelines(rst_domain(lightdom, title))

    # title = 'TV domain in system with multiple domains'
    # foo.writelines(rst_domain(tvdom, title))
    foo.close()
