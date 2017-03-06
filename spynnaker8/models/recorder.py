import logging
import neo
import os
import numpy
from datetime import datetime
import quantities as pq

from spynnaker.pyNN.models.recording_common import RecordingCommon
from spynnaker.pyNN.utilities import utility_calls
from spynnaker.pyNN.utilities import globals_variables
from spynnaker.pyNN import exceptions

logger = logging.getLogger(__name__)


class Recorder(RecordingCommon):
    def __init__(self, population):
        RecordingCommon.__init__(
            self, population,
            globals_variables.get_simulator().machine_time_step)
        self._recording_start_time = globals_variables.get_simulator().t

    @staticmethod
    def _get_io(filename):
        """
        Return a Neo IO instance, guessing the type based on the filename
        suffix.
        """
        logger.debug("Creating Neo IO for filename %s" % filename)
        dir = os.path.dirname(filename)
        utility_calls.check_directory_exists_and_create_if_not(dir)
        extension = os.path.splitext(filename)[1]
        if extension in ('.txt', '.ras', '.v', '.gsyn'):
            raise IOError(
                "ASCII-based formats are not currently supported for output"
                " data. Try using the file extension '.pkl' or '.h5'")
        elif extension in ('.h5',):
            return neo.io.NeoHdf5IO(filename=filename)
        elif extension in ('.pkl', '.pickle'):
            return neo.io.PickleIO(filename=filename)
        elif extension == '.mat':
            return neo.io.NeoMatlabIO(filename=filename)
        else:  # function to be improved later
            raise Exception("file extension %s not supported" % extension)

    def _extract_data(self, variables, clear, annotations):
        """ extracts data from the vertices and puts them into a neo block

        :param variables: the variables to extract
        :param clear: =if the variables should be cleared after reading
        :param annotations: annotations to put on the neo block
        :return: The neo block
        """

        data = neo.Block()
        # use really bad python to support pynn expectation that segments
        # exist as a parameter of neo block
        data.segments = list()

        # build segment for the current data to be gathered in
        segment = neo.Segment(
            name="segment{}".format(
                globals_variables.get_simulator().segment_counter),
            description=self._population.describe(),
            rec_datetime=datetime.now())

        # use really bad python because pynn expects it to be there.
        # add to the segments the new data
        data.segments.append(self._get_data(variables, clear, segment))

        # add fluff to the neo block
        data.name = self._population.label
        data.description = self._population.describe()
        data.rec_datetime = data.segments[0].rec_datetime
        data.annotate(**self._metadata())
        if annotations:
            data.annotate(**annotations)
        return data

    @staticmethod
    def _filter_recorded(filter_ids):
        record_ids = list()
        for id in range(0, len(filter_ids)):
            if filter_ids[id]:
                record_ids.append(id)
        return record_ids

    def _get_data(self, variables, clear, segment):

        # if all are needed to be extracted, extract each and plonk into the
        # neo block segment
        if variables == 'all':
            variables = ['spikes', 'v', 'gsyn_exc', 'gsyn_inh']

        for variable in variables:
            if variable == "spikes":
                t_stop = globals_variables.get_simulator().t * pq.ms  #
                # must run on all
                # MPI nodes
                spikes = self._get_recorded_variable('spikes')
                segment.spiketrains = [
                    neo.SpikeTrain(
                        times=spikes[atom_id],
                        t_start=self._recording_start_time,
                        t_stop=t_stop,
                        units='ms',
                        source_population=self._population.label,
                        source_id=int(atom_id),
                        source_index=self._population.id_to_index(atom_id))
                    for atom_id in sorted(self._filter_recorded(
                        self._indices_to_record['spikes']))]
            else:

                ids = sorted(self._filter_recorded(
                    self._indices_to_record[variable]))

                signal_array = self._get_recorded_variable(variable)
                t_start = self._recording_start_time
                sampling_period = self._sampling_interval * pq.ms
                if signal_array.size > 0:
                    channel_indices = numpy.array(
                        [self._population.id_to_index(atom_id)
                         for atom_id in ids])
                    units = self._population.find_units(variable)
                    source_ids = numpy.fromiter(ids, dtype=int)
                    segment.analogsignalarrays.append(
                        neo.AnalogSignalArray(
                            signal_array,
                            units=units,
                            t_start=t_start,
                            sampling_period=sampling_period,
                            name=variable,
                            source_population=self._population.label,
                            channel_index=channel_indices,
                            source_ids=source_ids))
        if clear:
            self._clear_recording(variables)

    def _metadata(self):
        metadata = {
            'size': self._population.size,
            'first_index': 0,
            'last_index': self._population.size,
            'first_id': int(self._population._first_id),
            'last_id': int(self._population._last_id),
            'label': self._population.label,
            'simulator': globals_variables.get_simulator().name,
        }
        metadata.update(self._population.annotations)
        metadata['dt'] = globals_variables.get_simulator().dt
        metadata['mpi_processes'] = \
            globals_variables.get_simulator().num_processes
        return metadata

    def _clear_recording(self, variables):
        # acquire buffer manager
        buffer_manager = globals_variables.get_simulator().buffer_manager

        # get machine vertices
        application_vertex = self._population._vertex
        machine_vertices = globals_variables.get_simulator().graph_mapper. \
            get_machine_vertices(application_vertex)

        # go through each machine vertex and clear recorded variables
        for machine_vertex in machine_vertices:

            # get placement
            placement = globals_variables.get_simulator().placements. \
                get_placement_of_vertex(machine_vertex)
            for variable in variables:
                if variable == 'spikes':
                    buffer_manager.clear_recorded_data(
                        placement.x, placement.y, placement.p,
                        machine_vertex.get_spikes_recording_region_id())
                elif variable == "v":
                    buffer_manager.clear_recorded_data(
                        placement.x, placement.y, placement.p,
                        machine_vertex.get_v_recording_region_id())
                elif variable == "gsyn_inh":
                    buffer_manager.clear_recorded_data(
                        placement.x, placement.y, placement.p,
                        machine_vertex.
                            get_gsyn_inhibitory_recording_region_id())
                elif variable == "gsyn_exc":
                    buffer_manager.clear_recorded_data(
                        placement.x, placement.y, placement.p,
                        machine_vertex.
                            get_gsyn_excitatory_recording_region_id())
                else:
                    raise exceptions.InvalidParameterType(
                        "The variable {} is not a recordable value".format(
                            variable))