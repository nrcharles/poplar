import csv
import datetime
import numpy as np
import random
from scipy.interpolate import interp1d
fmt ='%Y-%m-%d %H:%M:%S'

foo = csv.reader(open('./profiles.csv'))
BD = {}

for i in foo:
    lp = [float(j.strip()) for j in i[2:50]]
    dt = datetime.datetime.strptime(i[0][0:19],fmt).date()
    #, len(lp),lp
    BD[dt] = lp

def load(t):
    """ kw consumption as a funciton of time"""
    pass

def simple_profile(dt,mult=1.):
    offset = int(round(dt.hour*2.0))
    load_profile = [0.645, 0.615, 0.585, 0.569, 0.552, 0.541, 0.53,
    0.525, 0.521, 0.527, 0.534, 0.557, 0.581, 0.599, 0.617, 0.666, 0.715, 0.744,
    0.774, 0.768, 0.762, 0.754, 0.746, 0.747, 0.747, 0.743, 0.739, 0.72, 0.7,
    0.711, 0.722, 0.725, 0.728, 0.759, 0.79, 0.893, 0.997, 1.0, 0.995, 0.987,
    0.977, 0.937, 0.896, 0.857, 0.817, 0.757, 0.696, 0.667, 0.638]
    return load_profile[offset] * mult

def annual_2014(dt,mult=7.):
    mdt = datetime.date(2014,dt.month,dt.day)
    offset = (int(round(dt.hour*2.0))+0) % 48
    return BD[mdt][offset]*mult/4000.

class annual_2013(object):
    def __init__(self):
        self.mult = 7.
    def  __call__(self,dt):
        mdt = datetime.date(2013,dt.month,dt.day)
        offset = int(round(dt.hour*2.0))
        return BD[mdt][offset]*self.mult/4000.
    def __iter__(self):
        yield ['Annual Load',[]]

    def __repr__(self):
        return 'Load'

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

if __name__ == '__main__':
    #import datetime
    print simple_profile(datetime.datetime.now())
    print annual_2014(datetime.datetime.now())
    print annual_2014(datetime.datetime(2014,12,16,20))*4000/17.
    print annual_2014(datetime.datetime(2014,1,16,3))*4000/17.
