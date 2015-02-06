from caelum import eere
from loads import annual
from devices import Domain, IdealStorage
from devices import SimplePV, PVSystem, MPPTChargeController, SimpleChargeController

import matplotlib.pyplot as plt
# import matplotlib
# matplotlib.rcParams.update({'font.size': 18})

import sys
sys.stdout.flush()


def model(z):
    size, pv = z
    pv = max(pv, 0)
    size = max(size, 0)
    PLACE = (24.811468, 89.334329)
    SHS = Domain(load=annual(),
                 gen=PVSystem([MPPTChargeController([SimplePV(pv)])],
                 # gen=PVSystem([SimpleChargeController(SimplePV(pv))],
                              PLACE, 24.81, 180.),
                 storage=IdealStorage(size))
    for i in eere.EPWdata('418830'):
        SHS(i)
    SHS.storage.details()
    return SHS

def system_merit(domains):
    """calulate merit for various parameters"""
    a = 0
    t = 0
    c = 0
    p = 0
    r = 0
    g = 0
    l = 0
    G = 0
    C = 0
    nl = 0  # net load
    eg = 0
    for domain in domains:
        G += domain.STC()
        g += sum(domain.g)
        if domain.gen:
            g += domain.gen.losses()
            a += domain.gen.area()*10000  # cm^2
        if domain.storage:
            C += domain.storage.capacity
            eg += domain.storage.surplus
            nl += sum(domain.l) + domain.storage.shortfall
        else:
            nl += sum(domain.net_l)
            eg += domain.surplus
        l += sum(domain.l)
        t += domain.tox()
        c += domain.co2()
        p += domain.cost()
        r += domain.rvalue()

    I = t*c/a/G
    R = r/G
    P = p/G
    # print 'I (CTUh*gCO2eq/cm^2)', I
    # print 'R (?)', R
    # print 'P ($/w)', P
    # print "eta (%)", eta
    eta = round(nl/g * 100, 1)
    nt = nl*P*I*R/g
    print ', '.join([str(i) for i in [G, C, eta, P, I, R, t, a, c, r, g,
                                      eg, l, nl, nt]])

if __name__ == '__main__':
    plt.ion()
    plt.show()
    'G, C, eta, P, I, Rg, t, a, c, r, g, l, nt'
    print 'G,C,eta,P,I,R,t,a,c,r,g,eg,l,nl,nt'

    for i in range(25, 1000, 30):
        for j in range(5, 200, 5):
            system_merit([model([i, j])])
