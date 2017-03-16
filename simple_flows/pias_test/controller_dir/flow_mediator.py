'''
This is the core module since it handles the side of an ordinary
server. The module contains the main() function that setts up and
initializes the processes and the mediator for the server that this
program runs on. This script has to be
run on only ordinary servers (servers that just generate flows).

'''


# below imports are defined in this project
from flow_dir.flow_handler import Flow_Handler


# standard library imputs
import multiprocessing



class Flow_Mediator(object):

    __NUM_OF_STATIC_FLOWS = 3 # number of flows on this server
    __FLOW_PRIORITIES = [0x00, 0x08, 0x10]   # follows Linux ToS
    __FLOW_PRIORITY_PROB = [0.65, 0.25, 0.1] # priority prob
    '''
    This class acts as a mediator that interacts with the flows on this
    server. It provides an easy way of stopping all generated flows.
    '''

    def __init__(self, host_index, ip_addresses,
            dist_file, gen_factory):

        self._m_exit = multiprocessing.Event() # flag for temination

        # below array stores all the flows on this server (waiting/running flows)
        self._m_processes = []


        self._init_flows(host_index, ip_addresses,
                dist_file, gen_factory)

    '''
    Helper method to initialize the flows on
    this server. As it was agreed, a cluster of 4
    servers are communicating ==> 25 flows per
    server-to-server connection.
    '''
    def _init_flows(self, h_index,  ip_addresses,
            cdf_file, flow_factory):


        # run a loop and create flows
        # get the number of flows for each flow size and remote host
        num_of_hosts  = len(ip_addresses)
        flows_per_host = Flow_Mediator.__NUM_OF_STATIC_FLOWS/num_of_hosts

        last_host_flows = Flow_Mediator.__NUM_OF_STATIC_FLOWS - (num_of_hosts - 1) * flows_per_host

        # priority generator
        pr_generator = self._get_flow_priority()

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
                    flow_priority=pr_generator.next(),
                    host_index=h_index))

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
                flow_priority=pr_generator.next(),
                host_index=h_index))

            self._m_processes[-1].start() # start a flow

            m_index += 1 # update the index



    '''
    A helper to generate priorities for the flows
    '''
    def _get_flow_priority(self):
        # generate a number for each priority
        num_for_prior = [int(prob_pr * Flow_Mediator.
                         __NUM_OF_STATIC_FLOWS) for prob_pr in
                        Flow_Mediator.__FLOW_PRIORITY_PROB]
        # since int truncates floating point values, add
        # the remaining values to the lowest priority
        num_for_prior[0] += (Flow_Mediator.__NUM_OF_STATIC_FLOWS -
                            sum(num_for_prior))

        # generate a priority per request
        for idx in xrange(0, len(num_for_prior), 1):
            # for each priority
            # get flows of a particular priority
            prio_flows = num_for_prior[idx]
            for _ in xrange(0, prio_flows, 1):
                yield Flow_Mediator.__FLOW_PRIORITIES[idx]



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




