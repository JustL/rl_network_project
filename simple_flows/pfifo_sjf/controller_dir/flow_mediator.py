'''
This is the core module since it handles the side of an ordinary
server. The module contains the main() function that setts up and
initializes the processes and the mediator for the server that this
program runs on. This script has to be
run on only ordinary servers (servers that just generate flows).

'''


# below imports are defined in this project
from flow_dir.flow_handler import Flow_Handler
from flow_dir.flow_handler import CDF_Info
from flow_dir.flow_handler import LOWER_CDF_PARAM
from flow_dir.flow_handler import UPPER_CDF_PARAM


# standard library imputs
import multiprocessing

class Flow_Mediator(object):

    __NUM_OF_STATIC_FLOWS = 5  # number of flows on this server

    '''
    This class acts as a mediator that interacts with the flows on this
    server. It provides an easy way of stopping all generated flows.
    '''

    def __init__(self, host_index, ip_addresses,
            dist_file, gen_factory):

        self._m_exit = multiprocessing.Event() # flag for temination

        # below list stores running processes
        self._m_processes = []  # references to processes


        # initialize the shared flow info
        m_info = multiprocessing.Value(
                typecode_or_type=CDF_Info,
                lock=True)

        self._init_cdf_info(m_info, dist_file,
                gen_factory.create_generator())


        self._init_flows(host_index, ip_addresses,
                dist_file, gen_factory, m_info)



    '''
    Helper method that only takes a shared structure
    and initializes its fields to default values.

    Args:
        cdf_info   : a reference to the shared structure
        cdf_file   : a file that contains a CDF
        cdf_reader : a reader for computing avg cdf

    '''
    def _init_cdf_info(self, cdf_info, cdf_file,
            cdf_reader):

        # read the cdf file and then
        # compute average of the file
        cdf_reader.load_cdf(cdf_file)
        avg_value = cdf_reader.avg_cdf()


        with cdf_info.get_lock():
            cdf_info.cdf_min = long(
                    LOWER_CDF_PARAM * avg_value)

            cdf_info.cdf_avg = long(avg_value)
            cdf_info.cdf_max = long(
                    avg_value + UPPER_CDF_PARAM * avg_value)


    '''
    Helper method to initialize the flows on
    this server. As it was agreed, a cluster of 4
    servers are communicating ==> 25 flows per
    server-to-server connection.
    '''
    def _init_flows(self, h_index,  ip_addresses,
            cdf_file, flow_factory, info_struct):


        # run a loop and create flows
        # get the number of flows for each flow size and remote host
        num_of_hosts  = len(ip_addresses)
        flows_per_host = Flow_Mediator.__NUM_OF_STATIC_FLOWS/num_of_hosts

        last_host_flows = Flow_Mediator.__NUM_OF_STATIC_FLOWS - (num_of_hosts - 1) * flows_per_host

        m_index = 0 # indexing flows

        # loop through each of the flows and create a new Flow_Handler
        for host in xrange(0, num_of_hosts - 1, 1):


            # for each host create a few flows
            for _ in xrange(0, flows_per_host, 1):

                self._m_processes.append( Flow_Handler(
                    ip_address=ip_addresses[host],
                    flow_gen=flow_factory.create_generator(),
                    data_file = cdf_file,
                    flow_index=m_index,
                    host_index=h_index,
                    prio_sch = info_struct))

                self._m_processes[-1].start() # start a flow

                m_index += 1 # update the index

        #==========================================================
        # the remaining flows are sent to the last
        # host.
        for _ in xrange(0, last_host_flows, 1):
            self._m_processes.append( Flow_Handler(
                ip_address=ip_addresses[-1],
                flow_gen=flow_factory.create_generator(),
                data_file = cdf_file,
                flow_index=m_index,
                host_index=h_index,
                prio_sch=info_struct))

            self._m_processes[-1].start() # start a flow

            m_index += 1 # update the index

    '''
    Methods runs an infinite loop so that it could
    send updates to the RL server after a timeout expires.
    '''
    def start_updating(self):

        while not self._m_exit.is_set():
            pass



    '''
    Public method that closes sockets and kills all the processes.
    This method is only called when an exception poccurs
    '''
    def kill_processes(self):

        # set a signal that it is over
        self._m_exit.set()
        # go over all the processes and close sockets.
        # In addition, terminate the process.
        if self._m_processes:

            for prc in self._m_processes:
                if prc.is_alive():
                    prc.terminate()

            for prc in self._m_processes:
                prc.join()

        self._m_processes = None # release resources


        # Done running the program




