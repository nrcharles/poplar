# Copyright (C) 2015 Nathan Charles
#
# This program is free software. See terms in LICENSE file.
import matplotlib.pyplot as plt
import scipy.stats as stats
import numpy as np
import networkx as nx
import os
from misc import heatmap, latexify, fsify


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
    sep = ''.join(['='] * maxlen_k + [' '] + ['=']*maxlen_v) + '\n'
    tab.append(sep)
    tab.append('%s%s\n' % ('Parameter (units)'.ljust(maxlen_k+1), 'Value'))
    tab.append(sep)
    for k in d.iterkeys():
        tab.append('%s%s\n' % (k.ljust(maxlen_k+1), d[k]))
    tab.append(sep)
    return tab

def dict_to_latex_table(dictionary, caption, refname):

    table_str = ("\\begin{table}\n"
                 "\\centering\n"
                 "\\captionof{table}{%s} \\label{tab:%s}\n"
                 "\\begin{tabular}{@{}ll@{}}\n"
                 "\\toprule\n"
                 "Key & Value\\\\\n"
                 "\\midrule\n") % (latexify(caption), refname)

    for k in dictionary.iterkeys():
        table_str += ("%s & %s \\\\\n" % (latexify(k), dictionary[k]))

    table_str += ("\\bottomrule\n"
                  "\\end{tabular}\n"
                  "\\end{table}\n")

    return table_str


def report(device, figname='SHS', title=None):
    """Generate a PDF report of a storage device

    Args:
        device (object):
        figname (str):

    """
    domain = device
    figname = latexify(figname)
    if not title:
        title = figname
    fig = plt.figure()  # figsize=(8.5, 11))
    td = domain.details()
    soc_frequency = fig.add_subplot(221)
    soc_frequency.set_xlabel('SoC')
    soc_frequency.set_ylabel('Hourly Frequency')
    soc_frequency.set_title('Normalized SoC Histogram')
    soc_log = domain.soc_log()
    pp = np.array(soc_log)
    pp.sort()
    fit = stats.norm.pdf(pp, np.mean(pp), np.std(pp))

    soc_frequency.hist(soc_log, 40, normed=True)
    soc_frequency.plot(pp, fit)

    storage_soc = fig.add_subplot(222)
    storage_soc.set_xlabel('day')
    storage_soc.set_ylabel('hour')
    storage_soc.set_title('Storage State of Charge')
    soc = storage_soc.imshow(heatmap(soc_log), aspect='auto')
    soc_bar = fig.colorbar(soc)
    soc_bar.set_label('%')

    d_soc_frequency = fig.add_subplot(223)
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
                  "\\end{figure}\n") % (fsify(figname), latexify(title), figname)

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
    fig.savefig('%s.pdf' % fsify(figname))
    return table_str, figure_str

def freq_pdf(series, caption, basename):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xlabel('SoC')
    ax.set_ylabel('Frequency')
    # ax.set_title('Normalized SoC Histogram')
    pp = np.array(series)
    pp.sort()
    fit = stats.norm.pdf(pp, np.mean(pp), np.std(pp))

    ax.hist(series, 40, normed=True)
    ax.plot(pp, fit)
    filename = '%s.pdf' % basename
    fig.savefig(filename)
    print(latex_fig(filename, caption, basename))
    del(fig)

def latex_fig(filename, title, refname):

    parent_directory = os.getcwd().split('/')[-1]
    PATH = '../../src/python/poplar/doc/%s' % parent_directory

    figure_str = ("\\begin{figure}\n"
                  "\\centering\n"
                  "\\includegraphics[width=0.5\\linewidth]{%s/%s}\n"
                  "\\caption{%s} \\label{fig:%s}\n"
                  "\\end{figure}\n") % (PATH, filename, latexify(title), refname)
    return figure_str

def batt_report(device):
    """Generate a PDF report of a storage device

    Args:
        device (object):
        figname (str):

    """

    basename = fsify(latexify(str(device)))

    soc_log = device.soc_log()

    freq_pdf(soc_log, 'Hourly SoC frequency %s' % str(device), 'hourly_soc_freq_%s' % basename)

    heat_pdf(heatmap(soc_log), '%s Soc' % str(device), 'soc_%s' % basename)

    freq_pdf([np.mean(soc_log[i:i+23]) for i in range(0, 365*24, 24)],
             'Daily SoC frequency %s' % str(device),
             'daily_soc_freq_%s' % basename)

def heat_pdf(data, caption, basename):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xlabel('day')
    ax.set_ylabel('hour')
    #ax.set_title(title)
    bc = ax.imshow(data, aspect='auto')
    b4 = fig.colorbar(bc)
    b4.set_label('Wh')
    fig.tight_layout()
    filename = '%s.pdf' % basename
    fig.savefig(filename)
    print(latex_fig(filename, caption, basename))
    del(fig)

def multi_pdfs(domain):
    """Generate a PDF report of a domain

    Args:
        domain (object):
        figname (str):

    """

    basename = fsify(str(domain))

    for i in ['credits','debits','demand','source','balance']:
        heat_pdf(heatmap(domain.log_dict_to_list(i)), '%s %s' %(str(domain), i), '%s_%s' % (i, basename))

    print(dict_to_latex_table(domain.details(), str(domain), basename))


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
                  "\\end{figure}\n") % (fsify(figname), latexify(title), figname)

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
    fig.savefig('%s.pdf' % fsify(figname))
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
    fig.savefig('%s.pdf' % latexify(figname))


def rst_domain(domain, title):
    rst = []
    # rst.write(':orphan:\n\n')
    #tave_graph(domain, 'system_graph')
    multi_pdfs(domain)
    domain.report()
    parent_directory = os.getcwd().split('/')[-1]
    label = fsify(latexify(str(domain)))

    fig_rst = ("\n\n"
               ".. _%s:\n\n"
               ".. figure:: %s/%s.pdf\n\n"
               "   %s\n\n")

    rst += (fig_rst % (label, parent_directory, label, title))

    rst += (table_dict(domain.details()))


    return rst

def rst_graph(domain, title):
    rst = []
    # rst.write(':orphan:\n\n')
    save_graph(domain, 'system_graph')

    parent_directory = os.getcwd().split('/')[-1]

    label = fsify(latexify(str(domain)))

    graph_rst = ("\n\n"
                 ".. _%s_graph:\n\n"
                 ".. figure:: %s/system_graph.pdf\n\n"
                 "   %s graph\n\n")

    rst += (graph_rst % (label, parent_directory, title))

    return rst


def rst_batt(batt, title):
    rst = []

    batt.report()
    batt_report(batt)

    label = fsify(latexify(str(batt)))
    parent_directory = os.getcwd().split('/')[-1]

    fig_rst = ("\n\n"
               ".. _%s:\n\n"
               ".. figure:: %s/%s.pdf\n\n"
               "   %s\n\n")

    rst += (fig_rst % (label, parent_directory, label, title + ' battery'))

    return rst


if __name__ == '__main__':
    plt.ion()
    plt.show()
    'G, C, eta, P, I, Rg, t, a, c, r, g, l, nt'
