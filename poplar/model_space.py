from caelum import eere
from loads import annual
from devices import Domain, SimplePV, PVSystem
from storage import IdealStorage
from controllers import MPPTChargeController, SimpleChargeController

import matplotlib.pyplot as plt

import sys
sys.stdout.flush()


def model(z):
    size, pv = z
    pv = max(pv, 0)
    size = max(size, 0)
    PLACE = (24.811468, 89.334329)
    SHS = Domain([annual(),
                  PVSystem([MPPTChargeController([SimplePV(pv)])],
                            PLACE, 24.81, 180.),
                  IdealStorage(size)])
    for i in eere.EPWdata('418830'):
        SHS(i)
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
    o = 0
    for domain in domains:
        G += domain.STC()
        g += sum(domain.g)
        g += domain.parameter('losses')
        a += domain.parameter('area')
        C += domain.capacity()
        eg += domain.surplus
        nl += sum(domain.net_l)
        l += sum(domain.l)
        t += domain.tox()
        c += domain.co2()
        p += domain.cost()
        o += domain.outages
        r += domain.rvalue()

    I = t*c/a/G
    R = r/G
    P = p/G
    eta = round(nl/g * 100, 1)
    nt = nl*P*I*R/g
    return ', '.join([str(i) for i in [G, C, eta, P, I, R, t, a, c, r, o, g,
                                       eg, l, nl, nt]])


if __name__ == '__main__':
    plt.ion()
    plt.show()
    print 'G,C,eta,P,I,Rg,t,a,c,r,o,g,eg,l,nl,nt'

    for i in range(20, 250, 10):
        for j in range(5, 200, 5):
            print system_merit([model([i, j])])
