import spynnaker8 as p
from pyNN.utility.plotting import Figure, Panel, DataTable
import matplotlib.pyplot as plt
import numpy as np
from neo.core.spiketrain import SpikeTrain
from scipy.ndimage.measurements import label
from matplotlib.pyplot import legend
from idna.core import _alabel_prefix

import matplotlib.pyplot as plt

from neo.io import PyNNNumpyIO
from neo.io import AsciiSpikeTrainIO
from neo.io import PyNNTextIO
from example_graph_params import *
import time

timestr = time.strftime("%Y%m%d-%H%M%S")

to_plot_wgts = True
to_plot_wgts = False

p.setup(1)

simtime = 300
n_runs = 100
w0 = 0.0
pre_rates = np.arange(50, 55, 10) # pre-synaptic neuron rates
n_pre_rates = pre_rates.shape[0]
drive_rates = np.arange(0, 300, 15) # driving source rates
n_drive_rates = drive_rates.shape[0]
n_rates = drive_rates.size
max_out_rate = 200
output_file = "data2/fig2_"+timestr
output_ext = ".txt"

n_trans = np.zeros((n_pre_rates, max_out_rate+1)) # number of weight transitions for each spiking rate of the output neuron for 0 to 200
n_tot = np.zeros((n_pre_rates, max_out_rate+1)) # number of sims ran for each spiking rate of the output neuron (needed to calculate transition probability)

n_nrn = 200 # total number of neurons in each population

cell_params = {"i_offset":0.0,  "tau_ca2":150, "i_alpha":1., "i_ca2":3.,  'v_reset':-65}

pops = []
pops_src = []
pops_src2 = []
projections = []

for pre_r in pre_rates:
    for dr_r in drive_rates:
        pop_src = p.Population(n_nrn, p.SpikeSourcePoisson(rate=pre_r), label="src")
        pop_src2 = p.Population(n_nrn, p.SpikeSourcePoisson(rate=dr_r), label="drive")
        pop_ex = p.Population(n_nrn, p.extra_models.IFCurrExpCa2Concentration, cell_params, label="test")

        syn_plas = p.STDPMechanism(
            timing_dependence = p.PreOnly(A_plus = 0.15*w_max*w_mult, A_minus = 0.15*w_max*w_mult, th_v_mem=V_th, th_ca_up_l = Ca_th_l, th_ca_up_h = Ca_th_h2, th_ca_dn_l = Ca_th_l, th_ca_dn_h = Ca_th_h1),
            weight_dependence = p.WeightDependenceFusi(w_min=w_min*w_mult, w_max=w_max*w_mult, w_drift=w_drift*w_mult, th_w=th_w * w_mult), weight=w0*w_mult, delay=1.0)

        proj = p.Projection(
            pop_src,
            pop_ex,
            p.OneToOneConnector(),
            synapse_type=syn_plas, receptor_type='excitatory'
            )

        proj2 = p.Projection(pop_src2,  pop_ex,  p.OneToOneConnector(),
               synapse_type=p.StaticSynapse(weight=2.0),  receptor_type='excitatory')


        pop_ex.record(['spikes'])
        pops.append(pop_ex)
        pops_src.append(pop_src)
        pops_src2.append(pop_src2)
        projections.append(proj)
#         pop_src.record('spikes')
#         pop_src2.record('spikes')
nseg = 0
save_train = []
npops = len(pops)

for r in range(n_runs):
    p.run(simtime)
    new_rates = np.zeros(n_nrn, dtype=int)
    for i in range(npops):
        pop_ex = pops[i]
        proj = projections[i]

        pre_rate_ind = i / n_drive_rates
        dr_rate_ind = i - pre_rate_ind * n_drive_rates

        trains = pop_ex.get_data('spikes').segments[nseg].spiketrains
        new_w = proj.get('weight', format='list', with_address=False)

        for n in range(n_nrn):
            n_spikes = trains[n].shape[0]
            new_rate = int(round( n_spikes*1000.0/simtime ))
            print n,":",n_spikes, new_rate

            if new_rate>max_out_rate:
                continue
            if((w0*w_mult-th_w*w_mult)*(new_w[n] - th_w*w_mult)<0):
                n_trans[pre_rate_ind][new_rate] = n_trans[pre_rate_ind][new_rate] + 1
            n_tot[pre_rate_ind][new_rate] = n_tot[pre_rate_ind][new_rate] + 1


    nseg = nseg+1

    p.reset()
    probs = n_trans / n_tot
    probs.tofile(output_file+"_"+str(r)+output_ext, sep='\t', format='%10.5f')

    # need to reset the poisson sources, otherwise spike trains repeat too often
    for i in range(npops):
        pop_src = pops_src[i]
        pop_src2 = pops_src2[i]
        pre_rate_ind = i / n_drive_rates
        dr_rate_ind = i - pre_rate_ind * n_drive_rates
        pop_src.set(rate=pre_rates[pre_rate_ind])
        pop_src2.set(rate=drive_rates[dr_rate_ind])





#p.run(50)
probs = n_trans / n_tot

print probs

probs.tofile(output_file+"_full"+output_ext, sep='\t', format='%10.5f')

xs = np.arange(max_out_rate+1)
series1 = np.array(probs).astype(np.double)
s1mask = np.isfinite(series1)
print s1mask
#xs = np.tile(xs, (n_pre_rates,1))
print xs[s1mask[0,:]]

for i in range(n_pre_rates):
    plt.plot(xs[s1mask[i,:]], series1[i,:][s1mask[i,:]], linestyle='-', marker='o')

plt.show()



p.end()
print "\n job done"