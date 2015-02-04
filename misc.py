import numpy as np
#significant = lambda x,figures=3 : round(x,figures-int(np.floor(np.log10(x))))
def significant(number,figures=3):
    if number == 0.:
        return number
    order = np.ceil(np.log10(abs(number))).astype(int)
    if order > figures:
        return int(round(number,figures-order))
    else:
        return round(number,figures-order)

def heatmap(list_like):
    mangled_a = []
    for i in range(0, len(list_like), 24):
        mangled_a.append(list_like[i:i+23])
    data = np.array(mangled_a)
    #data = np.flipud(data)
    data = np.rot90(data,3)
    data = np.fliplr(data)
    return data
def module_temp(irradiance, weather_data):
    #todo: Maybe Sandia Module Temperature instead?                                                                                                                           
    #TamizhMani 2003
    t_amb = float(weather_data["Dry-bulb (C)"])
    wind_ms = float(weather_data['Wspd (m/s)'])
    t_module = .945*t_amb + .028*irradiance - 1.528*wind_ms + 4.3
    return t_module
