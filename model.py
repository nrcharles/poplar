# goal: model 1 year
from caelum import eere
from loads import annual_2013
from devices import Domain, PVSystem, MPPTChargeController, IdealStorage

from misc import heatmap

import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats

import sys
sys.stdout.flush()


def model(z):
    size, pv = z
    pv = max(pv, 0)
    isc = pv/12.5
    size = max(size, 0)
    PLACE = (24.811468, 89.334329)
    # SHS = Domain(load=DailyLoad([0,18,19,22,21,24],[0,0,1,1,0,0]),
    # SHS = Domain(load=spline_profile,
    SHS = Domain(load=annual_2013,
                 gen=PVSystem([MPPTChargeController(12.5, isc)],
                              PLACE, 24.81, 180.),
                 storage=IdealStorage(size))
    for i in eere.EPWdata('418830'):
        SHS(i)
    SHS.storage.details()
    return SHS


def report(domain, figname='SHS', title=None):
    if title is None:
        title = figname
    storage = domain.storage
    storage.details()
    pv = max(domain.g)
    size = storage.capacity
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(321)
    ax.set_title('Storage Frequency Histogram')
    pp = np.array(storage.state_series)
    pp.sort()
    fit = stats.norm.pdf(pp, np.mean(pp), np.std(pp))
    ax.hist(storage.state_series, 40, normed=True)
    ax.plot(pp, fit)
    ax2 = fig.add_subplot(322)
    ax2.set_xlabel('day')
    ax2.set_ylabel('hour')
    ax2.set_title('Storage State of Charge')
    soc = ax2.imshow(heatmap(storage.state_series), aspect='auto')
    b1 = fig.colorbar(soc)
    b1.set_label('%')
    ax3 = fig.add_subplot(323)
    ax3.set_title('Demand Profile')
    lp = ax3.imshow(heatmap(domain.l), aspect='auto')
    b2 = fig.colorbar(lp)
    b2.set_label('W')
    ax4 = fig.add_subplot(324)
    ax4.set_title('Generator Output')
    gp = ax4.imshow(heatmap(domain.g), aspect='auto')
    b3 = fig.colorbar(gp)
    b3.set_label('W')
    ax5 = fig.add_subplot(325)
    ax5.set_title('Battery Constraint')
    bc = ax5.imshow(heatmap(domain.d), aspect='auto')
    # b = ax5.imshow(heatmap(domain.d),aspect='auto',cmap = plt.cm.Greys_r)
    # b.set_clim(10,-20)
    b4 = fig.colorbar(bc)
    b4.set_label('W')
    td = domain.details()
    if domain.storage:
        td.update(domain.storage.details())
    s = '\n'.join(['%s:%s' % (k, td[k]) for k in td.iterkeys()])
    print s
    ax6 = fig.add_subplot(326)
    ax6.text(0., 0., s, fontsize=8)
    ax6.axis('off')
    print 'PV Array (kW) %s' % (pv/1000.)
    print 'Storage (wH) %s' % size
    print 'Loads/Depletion:?'
    system_merit([domain])
    # fig.suptitle(title)
    fig.tight_layout()
    # plt.show()
    # plt.draw()
    fig.savefig('%s.pdf' % figname)


def merit(z):
    size, pv = z
    domain = model((size, pv))
    load_shed = - domain.storage.shortfall
    im = plt.imshow(heatmap(domain.storage.state_series), aspect='auto')
    im.get_figure().canvas.flush_events()
    plt.draw()

    return domain.cost + domain.depletion + load_shed * 1  # 0.05


def unit_test():
    s = IdealStorage(100)
    d = 10 + s
    print d
    d = - 110 + s
    print d
    90 + s
    # s.details()
    if s.soc() != .9:
        print 'badness'


def system_merit(domains):
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
        if domain.storage:
            C += domain.storage.capacity
            eg += domain.storage.surplus
            nl += sum(domain.l) + domain.storage.shortfall
        else:
            nl += sum(domain.net_l)
            eg += domain.surplus
        l += sum(domain.l)
        a += domain.area*10000  # cm^2
        t += domain.tox
        c += domain.co2
        p += domain.cost
        r += domain.rvalue

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
    # unit_test()
    # from scipy import optimize
    # x0 = np.array([400.,70.])
    # r =  optimize.minimize(merit,x0)
    # r = optimize.basinhopping(model,x0,niter=1)
    # print r
    # s,p = r['x']
    # report(model((s,p)),'mppt_optimized_0.05_lolh',
    #        'SHS mppt controller sized at $0.05/lolh')
    # optimize.basinhopping(model,x0,niter=10)
    # optimize.anneal(model,x0,maxiter=10,upper=1000,lower=0)
    plt.show()
    'G, C, eta, P, I, R, t, a, c, r, g, l, nt'
    print 'G,C,eta,P,I,R,t,a,c,r,g,eg,l,nl,nt'

    for i in range(25, 1000, 30):
        for j in range(5, 200, 5):
            system_merit([model([i, j])])
