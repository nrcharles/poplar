import matplotlib.pyplot as plt
import scipy.stats as stats
import numpy as np
import networkx as nx
from misc import heatmap, latexify

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
    for i in domain.children:
        if i.classification is 'storage':
            storage = i
            td.update(storage.details())
    soc_frequency = fig.add_subplot(321)
    soc_frequency.set_xlabel('SoC')
    soc_frequency.set_ylabel('Frequency')
    soc_frequency.set_title('Normalized SoC Histogram')
    pp = np.array(domain.state_series)
    pp.sort()
    fit = stats.norm.pdf(pp, np.mean(pp), np.std(pp))

    soc_frequency.hist(domain.state_series, 40, normed=True)
    soc_frequency.plot(pp, fit)

    storage_soc = fig.add_subplot(322)
    storage_soc.set_xlabel('day')
    storage_soc.set_ylabel('hour')
    storage_soc.set_title('Storage State of Charge')
    soc = storage_soc.imshow(heatmap(domain.state_series), aspect='auto')
    soc_bar = fig.colorbar(soc)
    soc_bar.set_label('%')

    demand_profile = fig.add_subplot(323)
    demand_profile.set_xlabel('day')
    demand_profile.set_ylabel('hour')
    demand_profile.set_title('Demand Profile')
    dp = demand_profile.imshow(heatmap(domain.l), aspect='auto')
    dp_bar = fig.colorbar(dp)
    dp_bar.set_label('W')

    generator_o = fig.add_subplot(324)
    generator_o.set_xlabel('day')
    generator_o.set_ylabel('hour')
    generator_o.set_title('Generator Output')
    gp = generator_o.imshow(heatmap(domain.g), aspect='auto')
    gp_bar = fig.colorbar(gp)
    gp_bar.set_label('W')

    s_constraint = fig.add_subplot(325)
    s_constraint.set_xlabel('day')
    s_constraint.set_ylabel('hour')
    s_constraint.set_title('Domain Constraint')
    bc = s_constraint.imshow(heatmap(domain.d), aspect='auto')
    # cmap = plt.cm.Greys_r)
    b4 = fig.colorbar(bc)
    b4.set_label('W')

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
    pos = nx.spectral_layout(G)
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


if __name__ == '__main__':
    plt.ion()
    plt.show()
    'G, C, eta, P, I, Rg, t, a, c, r, g, l, nt'
