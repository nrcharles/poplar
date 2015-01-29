
#goal: model 1 year

from caelum import eere
from solpy import irradiation
from loads import simple_profile
import numpy as np
import matplotlib.pyplot as plt
import random
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

class SimplePV():
    def __init__(self,vnom,imp):
        self.vmp = vnom*1.2
        self.imp = imp
    def output(self, irr, t_cell=25):
        return self.vmp, self.imp*irr/1000.

class SimpleChargeController():
    def __init__(self, vnom, imp):
        self.imp = imp
        self.vnom = vnom
        self.vmpp = vnom * 1.2
        self.loss = 0
        self.array = SimplePV(vnom, imp)

    def __call__(self, irr):
        return self.output(irr)

    def output(self, irr, t_cell = None):
        v,i = self.array.output(irr)
        #i = irr/1000. * self.imp
        self.loss += (v - self.vnom) * i
        return self.vnom * i

    def losses(self):
        return self.loss

    def nameplate(self):
        return self.imp * self.vmpp

    def area(self):
        return self.nameplate()/1000./.2

    def tox(self):
        return self.nameplate()*.3

    def co2(self):
        #41g/kWh
        #life ~36500 hours of operation
        #1496.500 kg/kw
        return 1.496500 * self.nameplate()/1000.

    def cost(self):
        #assume a fixed cost for charge controller
        return self.nameplate()*.8+ 7#

class PVSystem(object):
    def __init__(self, shape, place, tilt, azimuth ):
        self.place = place
        self.tilt = tilt
        self.azimuth = azimuth
        self.shape = shape

    def p_dc(self, ins, t_cell=25):
        """dc power output"""
        total_dc = 0
        for i in self.shape:
            v,a = i.array.output(ins, t_cell)
            total_dc += v*a
        return total_dc

    def output(self, irr, t_cell = None):
        return sum([i.output(irr, t_cell) for i in self.shape])

    def area(self):
        return self.p_dc(1000.)/1000./.2

    def tox(self):
        return self.p_dc(1000.)*.3

    def co2(self):
        #41g/kWh
        #life ~36500 hours of operation
        #1496500 g/kw
        return 1496500 * self.p_dc(1000.)/1000.

    def losses(self):
        return sum([i.losses() for i in self.shape])

    def cost(self):
        #assume a fixed cost for charge controller
        return self.p_dc(1000.)*.8+ 7#

    def depletion(self):
        return self.cost()/20.

    def __call__(self,t):
        try:
            irr = irradiation.irradiation(t,self.place,t=self.tilt,array_azimuth=self.azimuth,model='p9')
            #no pwm
            #200 w panel 125 w because of no cc
            return self.output(irr)
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
        self.d = []

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

        self.d.append(d)
        return d

    def STC(self):
        if self.gen:
            return self.gen.p_dc(1000.)
        else:
            return 0.


    def autonomy(self):
        """this is a hack assumes hour time intervals"""
        #g_ave = sum(self.g)/len(self.g)
        l_med = np.median(self.l)
        return self.storage.capacity/l_med #hours

    def eta(self):
        return sum(self.l)/(sum(self.g)+self.gen.losses())

    def details(self):
        return {
        'gen losses (wh)' : round(self.gen.losses(),1),
        'desired load (wh)' : round(sum(self.l),1),
        'Autonomy (hours) (Median Load/C)' : round(self.autonomy(),1),
        'Domain Parts (USD)' : round(self.cost,2),
        'Domain depletion (USD)' : round(self.depletion,2),
        'A (m2)' : self.area,
        'Tox (CTUh)' : self.tox,
        'CO2 (gCO2 eq)' : self.co2,
        'eta T (%)' : round(self.eta()*100,1)
        }

    def __getattr__(self,name):
        v = 0
        for i in [self.gen,self.load,self.storage]:
        #return sum([method.name for 
            if hasattr(i, name):
                v += getattr(i,name)()
        return v

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

def noisy_profile(t):
    # +/1 10%
    return spline_profile(t)*(.9+random.random()/5.)

class LA(object):
    def __init__(self):
        self.useful = .5
        self.co2_g = 7000.
        self.tox_kg = 8.
        self.density = 50. #wh/kg
        self.cost_kg = 4.5
        self.cost_kw = .13

class IdealStorage(object):
    """Ideal Storage class
    no self discharge
    no efficiency losses
    no peukert
    no charge rate adjustments
    no thermal adjustements
    """
    def __init__(self, capacity, chemistry = None):
        "capacity is usable capacity in wh"
        if chemistry is None:
            self.chem = LA()
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
        self.c_in = []
        self.c_out = []
        self.r = 1.
    def rvalue(self):
        return self.r*self.loss_occurence

    def tox(self):
        return self.weight()*self.chem.tox_kg

    def co2(self):
        return self.weight()*self.chem.co2_g

    def weight(self):
        """weight in kg"""
        return self.capacity/self.chem.useful/self.chem.density

    def cost(self):
        fixed = self.weight()*self.chem.cost_kg
        return fixed

    def depletion(self):
        prospective = self.throughput/1000.*self.chem.cost_kw
        return prospective

    def power_io(self, power, hours=1.0):
        "power in watts"
        energy = power*hours
        self.in_use += hours

        if energy > 0:
            self.c_in.append(energy/self.capacity)
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
            self.c_out.append(energy/self.capacity)
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

    def autonomy(self):
        """ this might be stupid"""
        median_c= np.median(self.c_out)
        return abs(1.0/median_c)

    def __radd__(self,x):
        return self.power_io(x)

    def soc(self):
        return self.state/self.capacity

    def details(self):
        #print '#ELCC'
        #print '#LOLP'
        soc_series = np.array(self.state_series)
        results ={
        'shortfall (wh)' : round(self.shortfall,1), # ENS
        'surplus (wh)' : round(self.surplus,1),
        'full (hours)' : round(self.full_hours,1),
        'lolh (hours)' : round(self.drained_hours,1),
        'throughput (wh)' : round(self.throughput,1),
        'loss occurence (n)' : self.loss_occurence,
        'mean soc (%)' : round(soc_series.mean()*100,1),
        'median soc (%)' : round(np.median(soc_series)*100,1),
        'storage cost (US)' : round(self.cost(),2),
        'storage depletion (US)' : round(self.depletion(),2),
        'Autonomy 1/C (hours)': round(self.autonomy(),1)}
        return results

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
            gen=PVSystem([SimpleChargeController(12.5,isc)],PLACE,12.,180.),
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
    ax = fig.add_subplot(321)
    pp = np.array(storage.state_series)
    pp.sort()
    fit = stats.norm.pdf(pp, np.mean(pp), np.std(pp))
    ax.hist(storage.state_series,40,normed=True)
    ax.plot(pp,fit)
    ax.set_title('Storage Frequency Histogram')
    ax2 = fig.add_subplot(322)
    soc = ax2.imshow(heatmap(storage.state_series),aspect='auto')
    fig.colorbar(soc)
    ax2.set_title('Storage State of Charge')
    ax3 = fig.add_subplot(323)
    ax3.set_title('Load Profile')
    lp = ax3.imshow(heatmap(domain.l),aspect='auto')
    fig.colorbar(lp)
    ax4 = fig.add_subplot(324)
    ax4.set_title('Gen Profile')
    gp = ax4.imshow(heatmap(domain.g),aspect='auto')
    fig.colorbar(gp)
    ax5 = fig.add_subplot(325)
    ax5.set_title('Battery Constraint')
    b = ax5.imshow(heatmap(domain.d),aspect='auto')
    #b = ax5.imshow(heatmap(domain.d),aspect='auto',cmap = plt.cm.Greys_r)
    #b.set_clim(10,-20)
    fig.colorbar(b)
    ax6 = fig.add_subplot(326)
    td = domain.details()
    if domain.storage:
        td.update(domain.storage.details())
    s = '\n'.join(['%s:%s' %(k,td[k]) for k in td.iterkeys()])
    print s
    ax6.text(0.,0.,s,fontsize=8)
    ax6.axis('off')
    print 'PV Array (kW) %s'  % (pv/1000.)
    print 'Storage (wH) %s' % size
    system_merit([domain])
    plt.show()
    plt.draw()
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
    bcost = size * .125
    gcost = pv*.8
    #print gcost,bcost
    parts =  gcost + bcost
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

def system_merit(domains):
    a = 0
    t = 0
    c = 0
    p = 0
    r = 0
    g = 0
    l = 0
    G = 0
    for domain in domains:
        G += domain.STC()
        g += sum(domain.g)
        if domain.gen:
            g += domain.gen.losses()
        l += sum(domain.l)
        a += domain.area*10000 # cm^2
        t += domain.tox
        c += domain.co2
        p += domain.cost
        r += domain.rvalue

    print 't,a,c', t,a,c
    print G
    I = t*c/a/G
    R = r/G
    P = p/G
    print 'I (CTUh*gCO2eq/cm^2)', I
    print 'R (?)', R
    print 'P ($/w)', P
    print "eta (%)", round(l/g *100,1)
    nt = l*P*I*R/g
    print nt

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

