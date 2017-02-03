from interface_dir.flow_controller import Flow_Controller
from SimpleXMLRPCServer import SimpleXMLRPCServer
import threading
import Queue
import socket
from pyroute2 import IPRoute
from pyroute2.netlink.rtnl import RTM_DELQDISC
from pyroute2.netlink.rtnl import RTM_NEWQDISC
from pyroute2.netlink.rtnl import RTM_NEWTCLASS
from pyroute2.netlink.rtnl import TC_H_ROOT
from pyroute2.netlink import NetlinkError



class Traffic_Controller(Flow_Controller):

    __ACTION_TUPLE_LENGTH = 2     # so far : priority, rate
    __PRIORITY_LIMIT      = 7     # to ensure that priority does
                                  # not exceed limit


    __UPDATE_PARAMETER    = 20    # update traffic paramters only
                                  # after this number of sent updates
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

        self._m_cntrl = IPRoute()   # an interface to control traffic

        self._init_default_htb()    # for each interface set 'htb'
                                    # as the default


    '''
    Methid modified the default configurations of
    traffic engineering and resets them to htb.

    Raises:
        NetlinkErro: An error occured initializing TC subsystem.
        Exception:   Any other exception thrown during initialization.
    '''

    def _init_default_htb(self):
        idx = 0x10000

        # apply to all IPv4 interfaces
        interfaces = self._m_cntrl.get_addr(family=socket.AF_INET)

        for ifc in interfaces:
            # first of all add the interface to the ifc dictionary
            if_index = ifc['index']               # interface index
            self._m_infcs[ifc.get_attr('IFA_ADDRESS')] = if_index

            try:
                # delete the current discipline
                self._m_cntrl.tc(RTM_DELQDISC, None, if_index, 0,
                        parent=TC_H_ROOT)
            except Exception as exp:
                if isinstance(exp, NetlinkError) and exp.code == 2:
                    # nothing to delete
                    pass
                else:
                    # problem with the system

                    raise

            # scheduling has been deleted, add htb
            try:
                self._m_cntrl.tc(RTM_NEWQDISC, "htb", if_index,
                        idx, default=0)
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
            print "Terminating the update thread in Traffic_controller"
            self._m_upd_queue.put(None, block=True)
            print "Enqueued a None"
            self._m_upd_thread.join()
            self._m_cntrl.close()  # release system resources


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
            print "Invalid update tuple"
            return 'a'


        try:
            # try to send the updates to a background
            # thread
            self._m_upd_queue.put(params, block=False)

        except Queue.Full:
            pass  # ignore this exception

        print "---- update_flow_parameters returns now ----"

        return 'a'  # return to the rl server === the update received


    '''
    Helper method that uses the tc command to
    update the traffic engineering parameters.
    For further information, please refer to the
    tc command manual and the pyroute2 documentation.
    '''
    def _update_traffic_flow(self, if_idx, params):

        if self._m_msg_count != 0:
            self._m_msg_count -= 1
            return

        class_idx = 0x10000 + params["priority"] # since priority [1, 6]
        rate = params["rate"]
        parent = 0x10000


        try:
            self._m_cntrl.tc(
                    RTM_NEWTCLASS, "htb", if_idx,
                    class_idx, parent=parent,
                    rate="{0}kbit".format(rate))
            print "*** Traffic_Controller: has successfully updated ***"
        except NetlinkError as exp:
            # netlink error
            print "*** Traffic_Controller: NetlinkError: code = %i" % exp.code
            # wait a bit until another kernel message can be sent
            self._m_msg_count = Traffic_Controller.__UPDATE_PARAMETER
            print "Exception msg: %s", str(exp)
            #raise RuntimeError(exp.message + " NetlinkError")

        except:
            # some other excpetion
            print "*** Traffic_Controller: NOT NetlinkError ***"
            #raise RuntimeError(exp.message + " Not NetlinkError")


    def _wait_updates(self, upd_queue):

        # check whether it is needed to retrieve the interface index
        # TO DO: now only one interface is supported. Improve in the
        # future
        if self._m_server.server_address[0] in self._m_infcs:
            if_idx = self._m_infcs[self._m_server.server_address[0]] # retrieve interface index

            while 1: # run until the program is being terminated
                params = upd_queue.get(block=True)
                if params == None: # a None might be returned in order
                                   # to terminate this thread
                    return

                # apply the retrieved update
                self._update_traffic_flow(if_idx, params)

        else:
            # should never occur
            print "Invalid interface"
            # stop the server
            try:
                self._m_server.shutdown()      # close the server
                self._m_server.close_server()  # clean up the server
                return

            except:
                return


