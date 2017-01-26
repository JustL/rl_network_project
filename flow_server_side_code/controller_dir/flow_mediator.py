'''
This is the core module since it handles the side of an ordinary
server. The module contains the main() function that setts up and
initializes the processes and the mediator for the server that this
program runs on. Only this modules has to be executed in order to
make the Reinforcement Learning Project work. This script has to be
run on only ordinary servers (servers that just generate flows).

For the centralized Reinforcement Learning algorithm, please refer
to th 'rl_server_side_code' directory.
'''


# brlow imports are defined in this project
from flow_dir.flow_handler import Flow_Handler
from flow_dir.flow_impl import RL_Wait_Flow
from interface_dir.flow_controller import Flow_Controller
from interface_dir.flow_interfaces import WAIT_FLOW_VALID


# standard library imputs
from multiprocessing import Array, Queue, Lock
from Queue import Empty
import xmlrpclib
import sys
import math
import time


class Flow_Mediator(object):

    __SLEEP_TIME = 10          # default value 10 seconds
    __NUM_OF_STATIC_FLOWS = 75 # number of flows on this server
    __FLOW_SIZES =      [100000, 250000, 1000000, 500000000] # flow sizes (bytes)
    __FLOW_RATES =      [100, 200] # flow rate Kbit/s
    __FLOW_PRIORITIES = [0, 1, 2, 3, 4, 5, 6]   # 7 requires admin
    __FLOW_PRIORITY_PROB = [0.5, 0.2, 0.15, 0.05, 0.05, 0.03, 0.02] # priority porb
    __FLOW_PROBS =      [0.5, 0.35, 0.23, 0.02]   # flow probabilities
    '''
    This class acts as a mediator that interacts with the flows on this
    server, the remote rl algorithm server and the local remote procedire
    call server (local RPC server) in order to provide interfaces for
    the flows and the rl server to communicate with each others.
    '''

    def __init__(self, rl_server, ip_addresses,  controller, wf_type, wf_lock):
        self._m_proxy = None              # a connection to the RL server
        self._m_controller = controller   # for comminication with the local RPC
        # below array stores all the flows on this server (waiting/running flows)
        self._m_arr = Array(type(wf_type), [type(wf_type)()]*Flow_Mediator.__NUM_OF_STATIC_FLOWS, lock=wf_lock)
        self._m_cm_flows = Queue() # the structure that stores completed flows
        self._m_processes = [None]*Flow_Mediator.__NUM_OF_STATIC_FLOWS

        self._init_flows(rl_server, ip_addresses)

    '''
    Helper method to initialize the flows on
    this server. As it was agreed, a cluster of 4
    servers are communicating ==> 25 flows per
    server-to-server connection.
    '''
    def _init_flows(self, rl_server, ip_addresses):

        self._m_controller.start()         # start the traffic controller

        # try to connect to the remote rl server
        try:
            self._m_proxy = xmlrpclib.ServerProxy("http://" + rl_server[0] + ":" + str(rl_server[1]))
            self._m_proxy.test_connection() # this call does nothing. It is only used for testing the connection.
        except xmlrpclib.Fault as err:
            print "A fault has occurred"
            print "Fault code: %d" % err.faultCode
            print "Fault string: %s" % err.faultString

            self._m_controller.stop()          # stop the controller

            sys.exit(-1)            # error occurred

        # run a loop and create flows
        # get the number of flows for each flow size and remote host
        num_of_hosts  = len(ip_addresses)
        flows_per_host = self._get_nums_of_flows(num_of_hosts)

        # priority generator
        pr_generator = self._get_flow_priority()

        # loop through each of the flows and create a new Flow_Handler
        for host in xrange(num_of_hosts):
            # for each host create a few flows
            for f_idx in xrange(len(flows_per_host[host])):
                self._m_processes[host + f_idx] = Flow_Handler(ip_addresses[host], self._m_cm_flows,
                self._m_arr, flows_per_host[host][f_idx],
                Flow_Mediator.__FLOW_RATES[f_idx % len(Flow_Mediator.
                __FLOW_RATES)],
                host + f_idx, pr_generator.next())
                self._m_processes[host + f_idx].start() # start a flow


    '''
    Helper method that returns a tuple of
    flows for each type of flows.
    '''
    def _get_nums_of_flows(self, num_hosts):
        num_of_flow_types = len(Flow_Mediator.__FLOW_SIZES)
        num_flows = [0]*num_of_flow_types    # get a list that stores nums

        for idx in xrange(num_of_flow_types - 1):
            num_flows[idx] = int(math.ceil(Flow_Mediator.__FLOW_PROBS[idx]*Flow_Mediator.__NUN_OF_STATIC_FLOWS))

        # the number of the largest flows depends on the previous flows
        num_flows[-1] = (Flow_Mediator.__FLOW_SIZES - sum(num_flows)) if (Flow_Mediator.__FLOW_SIZES - sum(num_flows) > 0) else 1

        # all the remote clients (servers that belong to cluster)
        # have the smame numbers of different flows
        host_flows = [None]*num_hosts

        # compute a vector of flows per remote server
        host_vector = []
        for idx in xrange(num_of_flow_types):
            host_vector.append(num_flows[idx] / num_hosts)

        for idx in xrange(num_hosts-1):
            host_flows[idx] = host_vector

        # last host gets the remaining flows
        host_flows[-1] = [num_flows[idx] - host_vector[idx]*(num_hosts-1) for idx in xrange(num_of_flow_types)]

        # returns an array of flows
        return host_flows

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
        for pr in Flow_Mediator.__FLOW_PRIORITIES:
            # for each priority
            for _ in xrange(num_for_prior[pr]):
                yield pr



    '''
    Methods runs an infinite loop so that it could
    send updates to the RL server after a timeout expires.
    '''
    def start_updating(self):
        while 1:
            time.sleep(Flow_Mediator.__SLEEP_TIME) # sleep for a while

            # the timeout has expired. Send updates to the remote server
            send_wait_flows = []             # a list of waiting flows
            for wait_flow in self._m_arr:
                # append only valid flows (running/waiting flows)
                if send_wait_flows.is_valid() == WAIT_FLOW_VALID:
                    send_wait_flows.append(wait_flow.get_attributes())

            # done copying running/waiting flows
            # copy finihsed flows
            send_done_flows = []

            #keep reading until an exception occurs
            while 1:
                try:
                    send_done_flows.append(self._m_cm_flows.get())
                except Empty:
                    # done dequeueing the queue
                    pass
                except Exception as err:
                    print 'Error dequeing the queue'
                    print err.strerror
                    self.kill_processes()

            # By using RPC, send the lists to the RL server
            param_list = [self._m_controller.get_controller_address(), send_wait_flows, send_done_flows]
            self._m_proxy.pass_flow_info(param_list)

        '''
        Public method that closes sockets and kills all the processes.
        This method is only called when an exception poccurs
        '''
        def kill_processes(self):
            # go over all the processes and close sockets.
            # In addition, terminate the process.
            for prc in self._m_processes:
                prc.terminate()

            # Wait untill all the processes stop
            for prc in self._m_processes:
                prc.join()


            # In addition to killing the started flow processes,
            # stop running the traffic controller.
            self._m_controller.stop()

            # Before stopping the Flow_Mediator,
            # notify the remote rl server about it.
            self._m_proxy.unregister_server(self._m_controller.get_controller_address())

            sys.exit(0) # stop executing this process


if __name__ == '__main__':
    wait_flow_type = RL_Wait_Flow() # determines the C array's type
    wait_flow_lock = Lock() # the lock used for shared memrory array
    con = Flow_Controller(('127.0.0.1', 16850))
    mediator = Flow_Mediator(('127.0.0.1', 16850), ('127.0.0.1', 8000), con, wait_flow_type,  wait_flow_lock)
    # If the KeyboardInterrupt exception occurs, handle it
    try:
        mediator.start_updating()   # start running the flows
    finally: # no matter what happens, try to release the resources
        try:
            mediator.kill_processes()
        except Exception:
            print 'Exception occurred while closing the mediator'
            sys.exit(-1)

