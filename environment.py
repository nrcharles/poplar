weather = {}
time = None

def set_weather(iterable):
    for i, r in enumerate(iterable):
        weather[r['datetime']] = r

def update_time(dt):
    global time
    time = dt
