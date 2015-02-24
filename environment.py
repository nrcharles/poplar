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
time_series = []
time = None

def set_weather(iterable):
    for i, r in enumerate(iterable):
        weather[r['datetime']] = r

def update_time(dt):
    """Update global simulation time."""
    global time
    time_series.append(dt)
    time = dt
