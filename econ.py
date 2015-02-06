from __future__ import division
from misc import significant
import math
import matplotlib.pyplot as plt

# Volume Discount constant
VOLUME_CONSTANT = -0.8

CAP_PRICE_MW_2018 = 125.  # $/MW-day
CARBON_PRICE = 11.  #
REGULATION_PRICE = 60.  # $/MW/hour

# step function
p = lambda x, m, b: math.ceil(x/m)*(VOLUME_CONSTANT*math.log(math.ceil(x/m))+b)


def grid_value(domain):
    """grid value in Virtual Power Plant in a mature market"""

    cap_w = domain.STC()*domain.capacity_factor()
    cap_s = domain.storage.capacity  # w assuming 1C discharge
    e_v = domain.storage.surplus/1000. * .12

    cap_v = CAP_PRICE_MW_2018/1E6*cap_w*365.

    reg_v = REGULATION_PRICE/1E6*cap_s*365*24

    carbon_delta = sum(domain.g)/1000*.125
    results = {
        'e_v ($):': significant(e_v),
        'cap ($)': significant(cap_v),
        'reg ($):': significant(reg_v),
        'carbon delta (kg)': significant(carbon_delta)}
    return results


def scaling():
    """Scaling various system types

    This is interesting because it's step functions

    """
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    # ax.set_title('Storage Frequency Histogram')
    ws = range(1, 10000, 100)
    m = [p(x, 250, 1000) for x in range(1, 10000, 100)]
    ac = [p(x, 5000, 15000) for x in range(1, 10000, 100)]
    dc = [p(x, 1500, 7000) for x in range(1, 10000, 100)]
    ax.plot(ws, m, label='Micro Inverter')
    ax.plot(ws, ac,  label='AC Coupled')
    ax.plot(ws, dc, label='DC Coupled')
    ax.legend(loc='upper left')
    ax.set_ylabel('size (W)')
    ax.set_xlabel('Price (USD)')
    plt.draw()
    plt.show()
    plt.ion()
    fig.savefig('scaling.pdf')

# price of energy vs time
# plot(range(1,365),[7000./(5*2*x) for x in range(1,365)]),
# plot(range(1,365),[250./(5*.25*x) for x in range(1,365)]),
# plot(range(1,365),[17000./(5*8*x) for x in range(1,365)]),ylim(0,20)
# interesting because of when the sequences converge

# value of lost load Voll
# Loss ($/kW) = f(duration, season, time of day, notice)
# customer damage function (CDF)

if __name__ == '__main__':
    scaling()
