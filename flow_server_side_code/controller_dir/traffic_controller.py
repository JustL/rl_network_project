from interface_dir.flow_controller import Flow_Controller
from SimpleXMLRPCServer import SimpleXMLRPCServer
import threading
import Queue
import socket
from pyroute2 import IPRoute
import subprocess



class Traffic_Controller(Flow_Controller):

    __NIC_RATE            = "995mbit" # rate of a server's Nic card
    __ACTION_TUPLE_LENGTH = 2         # so far : priority, rate
    __PRIORITY_LIMIT      = 7         # to ensure that priority
                                      # does not exceed limit


    __UPDATE_PARAMETER    = 5         # update traffic paramters
                                      # only after this number
                                      # of sent updates
                                      # from an rl server
    '''
    The class is a concrete implementation of the Flow_Controller
    interface. The class runs an RPC server on a separate thread
    and handles all the requests coming from the remote RL machine.
    '''

    def __init__(self, ip_address):
        self._init_object(ip_address)


    '''
    Helper method to initialize all the needed fields
    of this flow controller.

    Args:
        ip_address : IPv4 address and port that the server listens on
    '''
    def _init_object(self, ip_address):
        self._m_server = SimpleXMLRPCServer(ip_address)

        self._m_msg_count = Traffic_Controller.__UPDATE_PARAMETER
                                    # this value prevetns the kernel
                                    # from update message overflow


        self._m_upd_queue =  None   # stores updates

        self._m_rcv_thread = None   # reference to the thread that
                                    # accepts updates

        self._m_upd_thread = None   # thread that performs updates

        self._m_infcs = {}          # for keeping track of IPv4 address :
                                    # interface matching


        self._init_default_sch()    # for each interface set the
                                    # selected scheduling qdisc
                                    # as the default


    '''
    Methid modified the default configurations of
    traffic engineering and resets them to the
    selected scheduler.

    Raises:
        NetlinkErro: An error occured initializing TC subsystem.
        Exception:   Any other exception thrown during initialization.
    '''

    def _init_default_sch(self):

        # apply to all IPv4 interfaces
        ip_cntrl = IPRoute()
        interfaces = ip_cntrl.get_addr(family=socket.AF_INET)

        ip_cntrl.close() # no need to use anymore

        for ifc in interfaces:
            # first of all add the interfaces to the ifc dictionary
            if_label = ifc.get_attr("IFA_LABEL") # interface label
            self._m_infcs[ifc.get_attr('IFA_ADDRESS')] = if_label


            try:
                subprocess.check_call(["tc", "qdisc", "del",
                    "dev", if_label, "root"],
                     stdin=None, stdout=None,
                     stderr=None, shell=False)

            except subprocess.CalledProcessError as exp:
                if exp.returncode == 2:
                    pass  # nothing to remove

                else:
                    raise # some other error



            # the default shceduler has been removed, add a new one
            try:
                # adding a new queueing discipline (prio since
                # it is classeful and similar
                # to the default pfifo_fast)
                subprocess.check_call(["tc", "qdisc", "add",
                    "dev", if_label, "root", "handle", "1:0",
                    "prio", "bands", "3", "priomap",
                    "1", "2", "2", "2", "1", "2", "0", "0",
                    "1", "1", "1", "1", "1", "1", "1", "1"],
                    stdin=None, stdout=None,
                    stderr=None, shell=False)


                # adding queues to the root queueing
                # discipline (prio has three classes)
                subprocess.check_call(["tc", "qdisc", "add",
                    "dev", if_label, "parent", "1:1", "tbf",
                    "rate", "200mbit", "burst", "5kb", "latency",
                    "70ms"], stdin=None, stdout=None,
                    stderr=None, shell=False)


                subprocess.check_call(["tc", "qdisc", "add",
                    "dev", if_label, "parent", "1:2", "tbf",
                    "rate", "600mbit", "burst", "5kb", "latency",
                    "70ms"], stdin=None, stdout=None,
                    stderr=None, shell=False)


                subprocess.check_call(["tc", "qdisc", "add",
                    "dev", if_label, "parent", "1:3", "tbf",
                    "rate", "300mbit", "burst", "5kb", "latency",
                    "70ms"], stdin=None, stdout=None,
                    stderr=None, shell=False)

            except:
                raise


    '''
    A method from the Flow_Controller interface.
    This method starts a new thread and the local
    SimpleXMLRPC server.
    '''
    def start_controller(self):

        # create shared types first
        m_queue = Queue.Queue(1) # store at most one update

        self._m_server.register_function(self.update_flow_parameters,
                'update_flow_parameters')
        # start a new thread for handling the RPC updates
        self._m_rcv_thread = threading.Thread(target=self._m_server.serve_forever)
        self._m_rcv_thread.start()

        # run a thread that performs traffic control updates
        self._m_upd_thread = threading.Thread(target=self._wait_updates, args=(m_queue, ))
        self._m_upd_thread.start()

        # keep references to the shared objects
        self._m_upd_queue = m_queue



    '''
    A way of stopping the RPC server.
    This method should usually be called when a session is done.
    '''
    def stop_controller(self):
        # since trying stopping an object that runs on another
        # thread, an excpetion might occur
        # This, however, should never happen since
        # only one thread can run at a time in the current
        # Python implementation


        # notify all threads that
        # the program is terminating
        try:
            self._m_server.shutdown()      # close the server
            self._m_server.close_server()  # clean up the server

            # wait until other threads terminate
            self._m_rcv_thread.join()

        except: # ignore all exceptions
            pass

        finally:
            # add to the shared queue a None
            # so that a background thread
            # would terminate

            # Since the background thread might have
            # stopped due to system errors, to handle
            # all such cases the queue is cleared
            # before enqueueing an None
            try:
                self._m_upd_queue.get(block=False)
            except Queue.Empty:
                pass

            finally:
                # the queue must be empty now
                print "Traffic_control: terminating the update",
                print "thread -- enqueueing a None"
                self._m_upd_queue.put(None, block=False)
                print "Traffic_Control: sucessfully enqueueing",
                print "a None, waiting for the thread to terminate\n"

                self._m_upd_thread.join()



    '''
    Public method used for getting the server's address.
    This is needed in order to enable the remote rl server
    pass upadtes to this server. The RL server must know
    the address of this server.
    '''
    def get_controller_address(self):
        # returns the tuple of IPv4 address
        # Because of the current implementation of Python,
        # no locking is needed. Only one thread can run at
        # a time.
        return self._m_server.server_address



    '''
    The interface that is used by a remote RL server to pass
    traffic engineering paramters to this server.
    This method handles all traffic updates accordingly to
    the passed params.
    '''

    def update_flow_parameters(self, params):
        if(len(params) != Traffic_Controller.__ACTION_TUPLE_LENGTH):
            # invalid update
            print "Traffic_Controller: update_flow_parameters:",
            print "invalid tuple from the rl server"
            return 'a'


        try:
            # try to send the updates to a background
            # thread
            self._m_upd_queue.put(params, block=False)

        except Queue.Full:
            pass  # ignore this exception


        return 'a'  # return to the rl server === the update received



    '''
    Helper method for converting a priority of a socket
    to a class index.

    Args:
        prio : socket priority

    return queueing discipline index
    '''
    def _convert_prio_to_class(self, prio):

        # the current implementation has
        # only three classes, so map prio to them
        default_class = 2 # best effort is mapped
                          # to second queue in Linux

        if prio >=6: # interactive flow
            return 1

        elif prio == 2:
            return 3


        return default_class


    '''
    Helper method that uses the tc command to
    update the traffic engineering parameters.
    For further information, please refer to the
    tc command manual and the pyroute2 documentation.

    Args:
        if_label : label of an ethernet interface
                   (e.g., 'eth0')
        params   : updates sent by a reinforcement server

    return update state
    '''
    def _update_traffic_flow(self, if_label, params):

        if self._m_msg_count != 0:

            self._m_msg_count -= 1

            return True


        # convert the received priorities to classes
        class_idx = "1:" + str(
                self._convert_prio_to_class(params["priority"]))
        rate = params["rate"]


        try:
            subprocess.check_call(
                    ["tc", "qdisc", "change", "dev", if_label,
                    "parent",  class_idx, "tbf",
                    "rate", "{0}mbit".format(rate), "burst",
                    "5kb", "latency", "70ms"], stdin=None,
                    stdout=None, stderr=None, shell=False)
            print "*** Traffic_Controller: _update_traffic_flow has",
            print "successfully executed ***\n"

        except subprocess.CalledProcessError as exp:
            pass
            # netlink error
            print "*** Traffic_Controller: NetlinkError:",
            print "code = %i" % exp.returncode
            print "Exception msg: %s", str(exp)


        except:
            # any other exception -- terminate the update thread
            print "Traffic_Controller: _update_traffic_flow:",
            print "unexpected exception"
            return False


        finally:
            # next update should wait for a bit
            self._m_msg_count = Traffic_Controller.__UPDATE_PARAMETER

        return True

    def _wait_updates(self, upd_queue):

        # check whether it is needed to retrieve the interface index
        # TO DO: now only one interface is supported. Improve in the
        # future
        if self._m_server.server_address[0] in self._m_infcs:
            if_label = self._m_infcs[self._m_server.server_address[0]]
            # retrieve interface label

            while 1: # run until the program is being terminated
                params = upd_queue.get(block=True)
                if params == None: # a None might be returned in order
                                   # to terminate this thread
                    return

                # apply the retrieved update
                # if anything wrong with the system, terminate
                if not self._update_traffic_flow(if_label, params):
                    try:
                        self._m_server.shutdown()
                        self._m_server.close_server()
                    except:
                        pass
                    finally:
                        return

        else:
            # should never occur
            # stop the server
            try:
                self._m_server.shutdown()      # close the server
                self._m_server.close_server()  # clean up the server

            except:
                pass
            finally:
                return


