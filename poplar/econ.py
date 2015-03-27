# Copyright (C) 2015 Nathan Charles
#
# This program is free software. See terms in LICENSE file.
"""Economic related functions."""

from __future__ import division
from misc import significant
import math
import matplotlib.pyplot as plt
import logging
logger = logging.getLogger(__name__)

# Volume Discount constant
VOLUME_CONSTANT = -0.8

CAP_PRICE_MW_2018 = 125.  # $/MW-day
CARBON_PRICE = 11.  #
REGULATION_PRICE = 60.  # $/MW/hour

# step function
p = lambda x, m, b: math.ceil(x/m)*(VOLUME_CONSTANT*math.log(math.ceil(x/m))+b)
# Where x is kwh, m is increment size and b is price floor constant


class Bid(object):

    """Bid Class."""

    def __init__(self, obj_id, wh, value):
        """Initialize.

        Args:
            obj_id (int): of device from which bid came.
            wh (float): amount of needed.
            value (float): at which energy will be bought.
        """
        self.obj_id = obj_id
        self.value = value
        self.wh = wh
        self.storage = False

    def __repr__(self):
        return '%s %s wh %s' % (self.obj_id, self.wh, self.value)


class Offer(object):

    """Offer class."""

    def __init__(self, obj_id, wh, value):
        """Initialize.

        Args:
            obj_id (int): of device from which offer came.
            wh (float): of energy needed.
            value (float): at which energy will be sold.
        """
        self.obj_id = obj_id
        self.value = value
        self.wh = wh
        self.storage = False

    def __repr__(self):
        return '%s %s wh %s' % (self.obj_id, self.wh, self.value)


def high_bid(nodes, offer=None):
    if offer is None:
        offer = Offer(0, 0, 0)
    high_bid = None
    bid_value = 0.
    for node in nodes:
        if hasattr(node, 'bid'):
            bid = node.bid()
            if bid:
                logger.debug('bid %s', bid)
                if (bid.value > bid_value) \
                    and (bid.obj_id != offer.obj_id) \
                    and not (bid.storage and offer.storage):
                    logger.debug('new high_bid %s', bid)
                    bid_value = bid.value
                    high_bid = bid
    return high_bid


def rank_bids(nodes):
    """Get and rand in order of priority, high to low."""
    bids = []
    for node in nodes:
        if hasattr(node, 'bid'):
            bid = node.bid()
            if bid:
                logger.debug('bid %s', bid)
                bids.append(bid)
    bids.sort(key=lambda x: x.value, reverse=True)
    return bids


def low_offer(nodes, bid):
    """Find lowest offer for bid."""
    if bid is None:
        bid = Bid(0, 0, 0)
    low_offer = None
    offer_value = 100.
    for node in nodes:
        if hasattr(node, 'offer'):
            offer = node.offer(bid.obj_id)
            # offer = node.offer()
            if offer:
                logger.debug('offer %s', offer)
                if (offer.value < offer_value) \
                    and (offer.obj_id != bid.obj_id) \
                    and not (bid.storage and offer.storage):
                    low_offer = offer
                    offer_value = offer.value
    return low_offer


def gini(list_of_values):
    """Calculate Gini coefficient for list of values."""
    sorted_list = sorted(list_of_values)
    height, area = 0, 0
    for value in sorted_list:
        height += value
        area += height - value / 2.
    fair_area = height * len(list_of_values) / 2
    return (fair_area - area) / fair_area


def grid_value(domain):
    """grid value in Virtual Power Plant in a mature market."""

    cap_w = domain.STC()*domain.capacity_factor()
    cap_s = domain.capacity()  # w assuming 1C discharge
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
    """Plot scaling various system types."""
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    # ax.set_title('Storage Frequency Histogram')
    ws = range(1, 10000, 100)
    m = [p(x, 250*1.3, 1000) for x in range(1, 10000, 100)]
    ac = [p(x, 5000*1.3, 15000) for x in range(1, 10000, 100)]
    dc = [p(x, 1500*1.3, 7000) for x in range(1, 10000, 100)]
    ax.plot(ws, m, label='Micro Inverter')
    ax.plot(ws, ac,  label='AC Coupled')
    ax.plot(ws, dc, label='DC Coupled')
    ax.legend(loc='upper left')
    ax.set_ylabel('Load (kWh)')
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

C = """
Item            Value                       Cost
====            ======================      ================
MPPT            % reduction of PV           $2 + power gates
DSM             % reduction of storage
interconnection reduction of storage        power conversion /grid extension
Net metering    sell excess energy          interconnection / policy
Regulation                                  interconneciton / policy
Capacity
Carbon
Energy

"""


if __name__ == '__main__':
    scaling()
