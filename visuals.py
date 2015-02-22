import matplotlib.pyplot as plt
import scipy.stats as stats
import numpy as np
import networkx as nx
from misc import heatmap, latexify

def table_dict(d):
    maxlen_k = 17
    maxlen_v = 5
    tab = []
    for k in d.iterkeys():
        if maxlen_k < len(k):
            l_k = len(k)
            l_v = len(str(d[k]))
            if l_k > maxlen_k:
                maxlen_k = l_k
            if l_v > maxlen_v:
                maxlen_v = l_v
    sep = ''.join(['='] * maxlen_k + [' '] + ['=']*maxlen_v)
    tab.append(sep)
    tab.append('%s%s' % ('Parameter (units)'.ljust(maxlen_k+1), 'Value'))
    tab.append(sep)
    for k in d.iterkeys():
        tab.append('%s%s' % (k.ljust(maxlen_k+1), d[k]))
    tab.append(sep)
    return tab


def report(domain, figname='SHS', title=None):
    """Generate a PDF report of a domain

    Args:
        domain (object):
        figname (str):

    """
    figname = latexify(figname)
    if not title:
        title = figname
    fig = plt.figure(figsize=(8.5, 11))
    td = domain.details()
    soc_frequency = fig.add_subplot(321)
    soc_frequency.set_xlabel('SoC')
    soc_frequency.set_ylabel('Hourly Frequency')
    soc_frequency.set_title('Normalized SoC Histogram')
    soc_log = domain.soc_log()
    print len(domain.state_series)
    print len(soc_log)
    pp = np.array(soc_log)
    pp.sort()
    fit = stats.norm.pdf(pp, np.mean(pp), np.std(pp))

    soc_frequency.hist(soc_log, 40, normed=True)
    soc_frequency.plot(pp, fit)

    storage_soc = fig.add_subplot(322)
    storage_soc.set_xlabel('day')
    storage_soc.set_ylabel('hour')
    storage_soc.set_title('Storage State of Charge')
    soc = storage_soc.imshow(heatmap(soc_log), aspect='auto')
    soc_bar = fig.colorbar(soc)
    soc_bar.set_label('%')

    d_soc_frequency = fig.add_subplot(323)
    d_soc_frequency.set_xlabel('SoC')
    d_soc_frequency.set_ylabel('Daily Frequency')
    d_soc_frequency.set_title('Normalized SoC Histogram')
    d_pp = [np.mean(soc_log[i:i+23]) for i in range(0, 365*24, 24)]
    d_pp.sort()
    fit2 = stats.norm.pdf(d_pp, np.mean(d_pp), np.std(d_pp))

    d_soc_frequency.hist(d_pp, 40, normed=True)
    d_soc_frequency.plot(d_pp, fit2)

    figure_str = ("\\begin{figure}\n"
                  "\\centering\n"
                  "\\includegraphics[width=\\linewidth]{../thesis/code/%s.pdf}\n"
                  "\\caption{%s} \\label{fig:%s}\n"
                  "\\end{figure}\n") % (figname, latexify(title), figname)

    table_str = ("\\begin{table}\n"
                 "\\centering\n"
                 "\\captionof{table}{%s} \\label{tab:%s}\n"
                 "\\begin{tabular}{@{}ll@{}}\n"
                 "\\toprule\n"
                 "Key & Value\\\\\n"
                 "\\midrule\n") % (latexify(title), figname)

    for k in td.iterkeys():
        table_str += ("%s & %s \\\\\n" % (latexify(k), td[k]))

    table_str += ("\\bottomrule\n"
                  "\\end{tabular}\n"
                  "\\end{table}\n")


    fig.tight_layout()
    fig.savefig('%s.pdf' % figname)
    return table_str, figure_str

def multi_report(domain, figname='SHS', title=None):
    """Generate a PDF report of a domain

    Args:
        domain (object):
        figname (str):

    """
    figname = latexify(figname)
    if not title:
        title = figname
    fig = plt.figure(figsize=(8.5, 11))
    td = domain.details()
    s_constraint = fig.add_subplot(321)
    s_constraint.set_xlabel('day')
    s_constraint.set_ylabel('hour')
    s_constraint.set_title('Domain Credits')
    bc = s_constraint.imshow(heatmap(domain.log_dict_to_list('credits')), aspect='auto')
    # cmap = plt.cm.Greys_r)
    b4 = fig.colorbar(bc)
    b4.set_label('Wh')

    storage_soc = fig.add_subplot(322)
    storage_soc.set_xlabel('day')
    storage_soc.set_ylabel('hour')
    storage_soc.set_title('Domain Debits')
    soc = storage_soc.imshow(heatmap(domain.log_dict_to_list('debits')), aspect='auto')
    soc_bar = fig.colorbar(soc)
    soc_bar.set_label('%')

    demand_profile = fig.add_subplot(323)
    demand_profile.set_xlabel('day')
    demand_profile.set_ylabel('hour')
    demand_profile.set_title('Demand Profile')
    dp = demand_profile.imshow(heatmap(domain.log_dict_to_list('demand')), aspect='auto')
    dp_bar = fig.colorbar(dp)
    dp_bar.set_label('Wh')

    generator_o = fig.add_subplot(324)
    generator_o.set_xlabel('day')
    generator_o.set_ylabel('hour')
    generator_o.set_title('Source Output')
    gp = generator_o.imshow(heatmap(domain.log_dict_to_list('source')), aspect='auto')
    gp_bar = fig.colorbar(gp)
    gp_bar.set_label('Wh')

    s_constraint = fig.add_subplot(325)
    s_constraint.set_xlabel('day')
    s_constraint.set_ylabel('hour')
    s_constraint.set_title('Domain Balance')
    bc = s_constraint.imshow(heatmap(domain.log_dict_to_list('balance')), aspect='auto')
    # cmap = plt.cm.Greys_r)
    b4 = fig.colorbar(bc)
    b4.set_label('Wh')

    figure_str = ("\\begin{figure}\n"
                  "\\centering\n"
                  "\\includegraphics[width=\\linewidth]{../thesis/code/%s.pdf}\n"
                  "\\caption{%s} \\label{fig:%s}\n"
                  "\\end{figure}\n") % (figname, latexify(title), figname)

    table_str = ("\\begin{table}\n"
                 "\\centering\n"
                 "\\captionof{table}{%s} \\label{tab:%s}\n"
                 "\\begin{tabular}{@{}ll@{}}\n"
                 "\\toprule\n"
                 "Key & Value\\\\\n"
                 "\\midrule\n") % (latexify(title), figname)

    for k in td.iterkeys():
        table_str += ("%s & %s \\\\\n" % (latexify(k), td[k]))

    table_str += ("\\bottomrule\n"
                  "\\end{tabular}\n"
                  "\\end{table}\n")

    domain_graph = fig.add_subplot(326)
    G = domain.graph()
    # pos = nx.spectral_layout(G)
    pos = nx.spring_layout(G)
    lpos = {}
    for i in pos.iterkeys():
        lpos[i] = pos[i] + [0, .15]
    nx.draw_networkx_nodes(G, pos=pos, ax=domain_graph, node_size=200)
    nx.draw_networkx_edges(G, pos=pos, ax=domain_graph)
    ts = nx.draw_networkx_labels(G, pos=lpos, font_size=7)  # rotation=45)

    for key in ts.iterkeys():
        ts[key].set_rotation(45)

    p = 1.2
    x1, x2 = domain_graph.get_xlim()
    y1, y2 = domain_graph.get_ylim()
    domain_graph.set_xlim(x1*p, x2*p)
    domain_graph.set_ylim(y1*p, y2*p)
    domain_graph.axis('off')
    fig.tight_layout()
    fig.savefig('%s.pdf' % figname)
    return table_str, figure_str

def save_graph(domain, figname):
    fig  = plt.figure()
    domain_graph = fig.add_subplot(111)
    G = domain.graph()
    # pos = nx.spectral_layout(G)
    pos = nx.spring_layout(G)
    lpos = {}
    for i in pos.iterkeys():
        lpos[i] = pos[i] + [0, .05]
    nx.draw_networkx_nodes(G, pos=pos, ax=domain_graph, node_size=200)
    nx.draw_networkx_edges(G, pos=pos, ax=domain_graph)
    ts = nx.draw_networkx_labels(G, pos=lpos, font_size=7)  # rotation=45)

    for key in ts.iterkeys():
        ts[key].set_rotation(45)

    p = 1.2
    x1, x2 = domain_graph.get_xlim()
    y1, y2 = domain_graph.get_ylim()
    domain_graph.set_xlim(x1*p, x2*p)
    domain_graph.set_ylim(y1*p, y2*p)
    domain_graph.axis('off')
    fig.tight_layout()
    fig.savefig('%s.pdf' % figname)


if __name__ == '__main__':
    plt.ion()
    plt.show()
    'G, C, eta, P, I, Rg, t, a, c, r, g, l, nt'
