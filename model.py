"""model off grid"""
#goal: model 1 year

from caelum import eere
from solpy import irradiation
from loads import simple_profile
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
from scipy.interpolate import interp1d

def heatmap(list_like):
    mangled_a = []
    for i in range(0, len(list_like), 24):
          mangled_a.append(list_like[i:i+23])
          data = np.array(mangled_a)
          data = np.rot90(data)
    return data

def g(t, w):
    PLACE = (24.811468, 89.334329)
    v = 12.5
    isc = w/v
    try:
        irr = irradiation.irradiation(t,PLACE,t=12.0,array_azimuth=180.0,model='p9')
        #no pwm
        #200 w panel 125 w because of no cc
        i = irr/1000.*isc
        return v*i
    except Exception as e:
        print e
        return 0

class SimpleChargeController():
    def __init__(self, vnom, isc):
        self.isc = isc
        self.vnom = vnom
    def __call__(self, irr):
        i = irr/1000. * self.isc
        return self.vnom * i
    def nameplate(self):
        return self.isc * self.vnom * 1.2
    def A(self):
        return self.nameplate()/.2
    def tox(self):
        return self.nameplate()*.3
    def co2(self):
        #30g/kWh
        return self.nameplate()*1.3

class PVGenerator(object):
    def __init__(self, conversion, place, tilt, azimuth ):
        self.place = place
        self.tilt = tilt
        self.azimuth = azimuth
        self.conversion = conversion
    def __call__(self,t):
        try:
            irr = irradiation.irradiation(t,self.place,t=self.tilt,array_azimuth=self.azimuth,model='p9')
            #no pwm
            #200 w panel 125 w because of no cc
            return self.conversion(irr)
        except Exception as e:
            print e
            return 0

class Domain(object):
    def __init__(self, load=None, storage=None, gen=None):
        self.load = load
        self.gen = gen
        self.storage = storage
        self.g = []
        self.l = []

    def __call__(self,record):
        if self.load:
            l_t = self.load(record['datetime'])
        else:
            l_t = 0

        if self.gen:
            g_t = self.gen(record)
        else:
            g_t = 0

        self.g.append(g_t)
        self.l.append(l_t)

        d = 0
        if self.storage:
            d = g_t - l_t + self.storage
        else:
            d = g_t - l_t
        return d


class DailyLoad(object):
    def __init__(self, hours, loads):
        self.profile = interp1d(hours, loads, kind='cubic')
    def __call__(self, dt):
        #offset = int(round(dt.hour*1.0))
        #offset = int(round(dt.hour*1.0))
        return self.profile(dt.hour)


load_profile = [0.645, 0.615, 0.585, 0.569, 0.552, 0.541, 0.53,
            0.525, 0.521, 0.527, 0.534, 0.557, 0.581, 0.599, 0.617, 0.666, 0.715, 0.744,
                0.774, 0.768, 0.762, 0.754, 0.746, 0.747, 0.747, 0.743, 0.739, 0.72, 0.7,
                    0.711, 0.722, 0.725, 0.728, 0.759, 0.79, 0.893, 0.997, 1.0, 0.995, 0.987,
                        0.977, 0.937, 0.896, 0.857, 0.817, 0.757, 0.696, 0.667, 0.638]
times = np.array(range(0,49))/2.
spline_profile = DailyLoad(times,np.array(load_profile)*17)

class IdealStorage(object):
    """Ideal Storage class
    no self discharge
    no efficiency losses
    no peukert
    no charge rate adjustments
    no thermal adjustements
    """
    def __init__(self,capacity):
        "capacity is usable capacity in wh"
        self.capacity = capacity
        self.state = capacity #start full
        self.throughput = 0.
        self.surplus = 0.
        self.drained_hours = 0.
        self.full_hours = 0.
        self.shortfall = 0.
        self.state_series = []
        self.in_use = 0.
        self.loss_occurence = 0

    def power_io(self, power, hours=1.0):
        "power in watts"
        energy = power*hours
        self.in_use += hours

        if energy > 0:
            max_in = self.capacity - self.state
            e_delta = min(energy,max_in)
            self.state += e_delta
            if e_delta != energy:
                surplus = energy - e_delta
                self.surplus += surplus
                active_time = surplus/energy * hours
                self.full_hours += active_time
            self.throughput += e_delta

        if energy < 0:
            max_out = self.state
            e_delta = - min(-energy, max_out)
            self.state += e_delta
            if e_delta != energy:
                shortfall = max_out + energy
                self.shortfall += shortfall
                shortfall_time = shortfall/energy * hours
                self.drained_hours += shortfall_time
                active_time = hours - shortfall_time
                self.loss_occurence += 1

        if energy == 0:
            if self.state is 0:
                self.drained_hours += hours
            if self.state == self.capacity:
                self.full_hours += hours
            e_delta =0

        self.state_series.append(self.soc())
        return e_delta - energy

    def __radd__(self,x):
        return self.power_io(x)

    def soc(self):
        return self.state/self.capacity

    def details(self):
        print '#ELCC'
        print '#LOLP'
        print 'shortfall ENS %s wh' %  self.shortfall
        print 'surplus %s wh' %  self.surplus
        print 'full_hours %s hours' % self.full_hours
        print 'lolh %s hours' % self.drained_hours
        print 'throughput %s wh' % self.throughput
        print 'loss occurences %s' % self.loss_occurence
        soc_series = np.array(self.state_series)
        print 'mean soc: %s' % soc_series.mean()
        print 'median soc: %s' % np.median(soc_series)

    def __repr__(self):
        return 'Soc: %s %%' % round(self.soc()*100,1)

def model(z):
    size,pv = z
    pv = max(pv,0)
    isc = pv/12.5
    size = max(size,0)
    PLACE = (24.811468, 89.334329)
    #SHS = Domain(load=DailyLoad([0,18,19,22,21,24],[0,0,1,1,0,0]),
    SHS = Domain(load=spline_profile,
            gen=PVGenerator(SimpleChargeController(12.5,isc),PLACE,12.,180.),
            storage=IdealStorage(size))
    print '%s Watts, %s Wh' % (pv,size)
    gen_t = 0
    load_t = 0
    s = []
    s_r = [747]
    test_storage = IdealStorage(size) #6kwh
    gseries = []
    l = []
    load_shed = 0
    gen_shed = 0
    for i in eere.EPWdata('418830'):
        g_t = g(i,pv)
        #print g_t, SHS.gen(i)
        l_t = simple_profile(i['datetime'],17)
        d1 = SHS(i)
        d = g_t - l_t + test_storage
        #print d1,d
        if d > 0:
            load_shed += d
            net_l = l_t - d
        else:
            net_l = l_t

        if d < 0:
            gen_shed += d
            net_g = g_t + d
        else:
            net_g = g_t

        l.append(net_l)
        load_t += net_l
        gseries.append(net_g)
        gen_t += net_g

        delta = g_t - l_t
        s.append(delta)
        s_r.append(s_r[-1]+delta)
#    print g_t, l_t, delta, test_storage

    #print gen_t/1000, 'kwh'
    #print load_t/1000., 'kwh'
    #annual = (gen_t - load_t)/1000.0
    #print annual, 'kwh'
    #print 'load shed', load_shed, test_storage.shortfall
    #print 'gen_shed', gen_shed, test_storage.surplus

    #print max(s_r)
    #print min(s_r)
    print 'SHS'
    SHS.storage.details()
    print 'test'
    test_storage.details()
    print 'total load', sum(SHS.l)
    print 'total gen', sum(SHS.g)
    #print test_storage
    print
    return SHS #test_storage,gseries,l,s

#def report(storage,gseries,l,s,figname='state'):
def report(domain,figname='SHS'):
    storage = domain.storage
    storage.details()
    pv = max(domain.g)
    size = storage.capacity
    fig = plt.figure(figsize=(8.5,11))
    ax = fig.add_subplot(221)
    pp = np.array(storage.state_series)
    pp.sort()
    fit = stats.norm.pdf(pp, np.mean(pp), np.std(pp))
    ax.hist(storage.state_series,40,normed=True)
    ax.plot(pp,fit)
    ax.set_title('Storage Frequency Histogram')
    ax2 = fig.add_subplot(222)
    ax2.imshow(heatmap(storage.state_series),aspect='auto')
    ax2.set_title('Storage State of Charge')
    ax3 = fig.add_subplot(223)
    ax3.imshow(heatmap(domain.l),aspect='auto')
    ax3.set_title('Load Profile')
    ax4 = fig.add_subplot(224)
    ax4.set_title('Gen Profile')
    ax4.imshow(heatmap(domain.g),aspect='auto')
    print 'PV Array %s kW' % (pv/1000.)
    print 'Storage %s wH' % size
    plt.show()
    plt.draw()
    print 'Autonomy:???'
    fig.savefig('%s.pdf' % figname)

def merit(z):
    size,pv = z
    domain = model((size,pv))
    #test_storage, gseris, l, s = model((size,pv))
    #return test_storage,gseries,l,s
    #analyse
    #merit = (test_storage.surplus+test_storage.shortfall)**2
    #bmerit = (test_storage.drained_hours*2 + test_storage.full_hours)**2
    #gmerit = (gen_t/1000.-load_t/1000.)**2
    #print 'Merit', bmerit, gmerit
    load_shed = - domain.storage.shortfall
    bprice = size * .125
    gprice = pv*.8
    #print gprice,bprice
    parts =  gprice + bprice
    print 'Merit'
    print '$', parts, 'shortfall', load_shed
    #print parts + load_shed
    #IM.set_array(heatmap(test_storage.state_series))#,aspect='auto')
    #f = plt.figure()
    #f.clear()
    im = plt.imshow(heatmap(domain.storage.state_series),aspect='auto')
    im.get_figure().canvas.flush_events()
    #plt.show(block=False)
    plt.draw()
    print
    #f.canvas.flush_events()

    return parts + load_shed

def unit_test():
    s = IdealStorage(100)
    d =  10 + s
    print d
    d = - 110 + s
    print d
    90 + s
    #s.details()
    if s.soc() != .9:
        print 'badness'

if __name__ == '__main__':
    plt.ion()
    unit_test()
    from scipy import optimize
    x0 = np.array([400.,70.])
    r =  optimize.minimize(merit,x0)
    print r
    s,p = r['x']
    report(model((s,p)))
    #optimize.basinhopping(model,x0,niter=10)
    #optimize.anneal(model,x0,maxiter=10,upper=1000,lower=0)
    plt.show()

