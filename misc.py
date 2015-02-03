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
