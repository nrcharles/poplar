# Copyright (C) 2015 Nathan Charles
#
# This program is free software. See terms in LICENSE file.
"""Environmental Variables.

Environment holds weather and global variables in shared memory.

Attributes:
    weather (dict): all availible weather data.
    time (datetime): current time in environment.
    time_series (list): history of time.

"""
import os
SRC_PATH = os.path.dirname(os.path.abspath(__file__))

weather = {}
time = None
time_series = []
network = None
total_time = 0.  # hours

def set_weather(iterable):
    for i, r in enumerate(iterable):
        weather[r['datetime']] = r

def update_time(dt, hours=1.):
    """Update global simulation time."""
    global time
    global total_time
    total_time += hours
    time_series.append(dt)
    time = dt

def reset():
    global time_series
    global network
    global total_time
    time_series = []
    network = None
    total_time = 0
