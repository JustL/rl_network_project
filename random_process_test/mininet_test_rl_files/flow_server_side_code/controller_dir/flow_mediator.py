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


# below imports are defined in this project
from flow_dir.flow_handler import Flow_Handler


# standard library imputs
import multiprocessing
import Queue
import xmlrpclib
import time


class Flow_Mediator(object):

    __SLEEP_TIME = 20           # value for update period in seconds
    __NUM_OF_STATIC_FLOWS = 3   # number of flows on this server
    __MAX_QUEUE_SIZE      = 20  # size of completed flows
    __FLOW_RATES =      [100000, 200000] # flow rate bit/s
    __FLOW_PRIORITIES = [0, 2, 4, 6]     # follws Linux
    __FLOW_PRIORITY_PROB = [0.65, 0.10, 0.2, 0.05] # priority porb
    '''
    This class acts as a mediator that interacts with the flows on this
    server, the remote rl algorithm server and the local remote procedire
    call server (local RPC server) in order to provide interfaces for
    the flows and the rl server to communicate with each others.
    '''

    def __init__(self, host_index, rl_server, ip_addresses,
            controller, wf_type, gen_factory, cdf_file):
        self._m_proxy = None              # a connection to the RL server
        self._m_controller = controller   # for comminication with
                                          # the local RPC
        self._m_exit = multiprocessing.Event() # flag for temination

        # below array stores all the flows on this server (waiting/running flows)
        self._m_arr = multiprocessing.Array(type(wf_type),
                [type(wf_type)()]*Flow_Mediator.__NUM_OF_STATIC_FLOWS,
                lock=multiprocessing.Lock())

        self._m_cm_flows = multiprocessing.Queue(
            Flow_Mediator.__MAX_QUEUE_SIZE)          # the structure that
                                                     # stores completed
                                                     # flows (maxsize is a
                                                     # hard-coded vale
                                                     # that should be
                                                     # somehow realted
                                                     # to rl algm.

        self._m_processes = []


        self._init_flows(host_index, rl_server,
                ip_addresses, gen_factory, cdf_file)

    '''
    Helper method to initialize the flows on
    this server. As it was agreed, a cluster of 4
    servers are communicating ==> 25 flows per
    server-to-server connection.
    '''
    def _init_flows(self, h_index, rl_server,
            ip_addresses, gen_factory, dist_file):


        # try to connect to the remote rl server
        try:
            self._m_proxy = xmlrpclib.ServerProxy("http://" + rl_server[0] + ":" + str(rl_server[1]))
            self._m_proxy.test_connection() # this call does nothing. It is only used for testing the connection.
        except xmlrpclib.Fault as err:
            print "A fault has occurred"
            print "Fault code: %d" % err.faultCode
            print "Fault string: %s" % err.faultString

            raise

        except:
            print "Some other exception related to RPC server"

            raise

        self._m_controller.start_controller() # start the traffic
                                              # controller


        # run a loop and create flows
        # get the number of flows for each flow size and remote host
        num_of_hosts   = len(ip_addresses)
        flows_per_host = Flow_Mediator.__NUM_OF_STATIC_FLOWS/num_of_hosts

        last_host_flows = Flow_Mediator.__NUM_OF_STATIC_FLOWS -  (num_of_hosts - 1) * flows_per_host


        # priority generator
        pr_generator = self._get_flow_priority()

        m_index = 0 # for indexing flows

        # loop through each of the flows and create a new Flow_Handler
        for host in xrange(0, num_of_hosts-1, 1):
            # for each host create a few flows

            # create flows per hosts
            for _ in xrange(0, flows_per_host, 1):
                self._m_processes.append( Flow_Handler(
                    ip_address=ip_addresses[host],
                    cmp_queue=self._m_cm_flows,
                    inc_arr=self._m_arr,
                    flow_gen=gen_factory.create_generator(),
                    cdf_file = dist_file,
                    flow_pref_rate=Flow_Mediator.__FLOW_RATES[m_index %
                    len(Flow_Mediator.__FLOW_RATES)],
                    flow_index=m_index,
                    flow_priority=pr_generator.next(),
                    host_index=h_index))

                self._m_processes[-1].start() # start a flow
                m_index += 1                  # update the index


        # created flows for the firs remote servers
        # creating flows for the last server

        try:
            for _ in xrange(0, last_host_flows, 1):
                self._m_processes.append( Flow_Handler(
                ip_address=ip_addresses[-1],
                cmp_queue=self._m_cm_flows,
                inc_arr=self._m_arr,
                flow_gen=gen_factory.create_generator(),
                cdf_file = dist_file,
                flow_pref_rate=Flow_Mediator.__FLOW_RATES[m_index %
                len(Flow_Mediator.__FLOW_RATES)],
                flow_index=m_index,
                flow_priority=pr_generator.next(),
                host_index=h_index))


                self._m_processes[-1].start() # start a flow
                m_index += 1                  # update the index
        except Exception as exp:
            print exp

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
            time.sleep(Flow_Mediator.__SLEEP_TIME) # sleep for a while

            if self._m_exit.is_set(): # means another thread has closed
                break;

            # the timeout has expired. Send updates to the remote server
            send_wait_flows = []             # a list of waiting flows
            for wait_flow in self._m_arr:
                # append only valid flows (running/waiting flows)
                if wait_flow.is_valid():
                    send_wait_flows.append(wait_flow.get_attributes())

            # done copying running/waiting flows
            # copy finihsed flows
            send_done_flows = []


            #keep reading until an exception occurs
            try:
                while 1:
                    send_done_flows.append(self._m_cm_flows.
                            get(block=False).get_attributes())

            except Queue.Empty:
                # done dequeueing the queue
                pass
            except:
                # some other exception occured
                pass

            # By using RPC, send the lists to the RL server

            # this cannot happen in the first prototype, but it
            # might happen later
            if not send_wait_flows and not send_done_flows:
                continue

            param_list = (self._m_controller.get_controller_address(),
                    send_wait_flows, send_done_flows)
            try:
                # an exception might be thrown if the rl server
                # has been closed
                self._m_proxy.pass_flow_info(param_list)
            except:
                # means the proxy has been closed
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


        # In addition to killing the started flow processes,
        # stop running the traffic controller.
        print "Stopping my controller"
        self._m_controller.stop_controller()

        print "Controller has been stopped"
        # Before stopping the Flow_Mediator,
        # notify the remote rl server about it.
        try:
            self._m_proxy.unregister_server(
                    self._m_controller.get_controller_address())
        except:
            # remote rl server has been closed
            pass # do nothing



    '''
    Sets the number of flows that this flow mediator
    generates overall/distributes among all remote serverers.

    Args:
        flow_number : total number of flows for a host
    '''
    @staticmethod
    def set_flow_number(flow_number):
        if flow_number > 0:
            Flow_Mediator.__NUM_OF_STATIC_FLOWS = flow_number
