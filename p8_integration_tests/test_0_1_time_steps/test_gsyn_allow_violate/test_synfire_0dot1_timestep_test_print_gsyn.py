"""
Synfirechain-like example
"""
# general imports
import numpy
import os
import pickle
from p8_integration_tests.base_test_case import BaseTestCase
from p8_integration_tests.scripts.synfire_run import TestRun
import spynnaker.spike_checker as spike_checker
from spynnaker8.utilities import neo_convertor
from spynnaker8.spynakker_plotting import SpynakkerPanel
from spinnman.exceptions import SpinnmanTimeoutException
from unittest import SkipTest
from pyNN.utility.plotting import Figure
import matplotlib.pyplot as plt

n_neurons = 200  # number of neurons in each population
max_delay = 14.4
timestep = 0.1
neurons_per_core = n_neurons/2
delay = 1.7
runtime = 500
gsyn_path = os.path.dirname(os.path.abspath(__file__))
gsyn_path = os.path.join(gsyn_path, "gsyn.pickle")
synfire_run = TestRun()


class TestPrintGsyn(BaseTestCase):
    """
    tests the printing of get gsyn given a simulation
    """

    def test_get_gsyn(self):
        try:
            synfire_run.do_run(n_neurons, max_delay=max_delay,
                               time_step=timestep,
                               neurons_per_core=neurons_per_core, delay=delay,
                               run_times=[runtime], gsyn_path_exc=gsyn_path)
            spikes = synfire_run.get_output_pop_spikes_numpy()
            g_syn = synfire_run.get_output_pop_gsyn_exc_numpy()
            spike_checker.synfire_spike_checker(spikes, n_neurons)
            with open(gsyn_path, "r") as gsyn_file:
                gsyn2_neo = pickle.load(gsyn_file)
            gsyn2_numpy = neo_convertor.convert_data(gsyn2_neo, run=0,
                                                     name="gsyn_exc")
            self.assertTrue(numpy.allclose(g_syn, gsyn2_numpy))
            os.remove(gsyn_path)
        except SpinnmanTimeoutException as ex:
            # System intentional overload so may error
            raise SkipTest(ex)


if __name__ == '__main__':
    synfire_run.do_run(n_neurons, max_delay=max_delay, time_step=timestep,
                       neurons_per_core=neurons_per_core, delay=delay,
                       run_times=[runtime], gsyn_path_exc=gsyn_path)
    spikes = synfire_run.get_output_pop_spikes_numpy()
    g_syn = synfire_run.get_output_pop_gsyn_exc_numpy()
    spike_checker.synfire_spike_checker(spikes, n_neurons)
    with open(gsyn_path, "r") as gsyn_file:
        gsyn2_neo = pickle.load(gsyn_file)
    gsyn2_numpy = neo_convertor.convert_data(gsyn2_neo, run=0, name="gsyn_exc")
    print len(spikes)
    Figure(SpynakkerPanel(spikes, yticks=True, xticks=True, markersize=4,
                          xlim=(0, runtime)),
           SpynakkerPanel(gsyn2_neo, yticks=True),
           title="TestPrintGsyn".format(delay),
           annotations="generated by {}".format(__file__))
    plt.show()
    os.remove(gsyn_path)
