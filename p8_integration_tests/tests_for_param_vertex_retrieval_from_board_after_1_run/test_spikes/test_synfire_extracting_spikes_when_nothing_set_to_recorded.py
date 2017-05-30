"""
Synfirechain-like example
"""
# general imports
from p8_integration_tests.scripts.synfire_run import TestRun
from p8_integration_tests.base_test_case import BaseTestCase

from spinn_front_end_common.utilities.exceptions import ConfigurationException

n_neurons = 20  # number of neurons in each population
runtime = 200
delay = 30
neurons_per_core = None
synfire_run = TestRun()
record = False
get_spikes = True


class SynfireExtractingSpikesWhenNothingSetToRecorded(BaseTestCase):
    """
    tests the printing of get gsyn given a simulation
    """

    def test_cause_error(self):
        with self.assertRaises(ConfigurationException):
            synfire_run.do_run(n_neurons, neurons_per_core=neurons_per_core,
                               delay=delay, run_times=[runtime], record=record,
                               get_spikes=get_spikes)


if __name__ == '__main__':
    synfire_run.do_run(n_neurons, neurons_per_core=neurons_per_core,
                       delay=delay, run_times=[runtime], record=record,
                       get_spikes=get_spikes)