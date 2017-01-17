from interface_dir.flow_controller import Flow_Controller
from SimpleXMLRPCServer import SimpleXMLRPCServer
import threading
import socket
from pyroute2 import IPRoute


class Traffic_Controller(Flow_Controller):

    __ACTION_TUPLE_LENGTH = 3     # so far : ip address, priority, rate
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
        self._m_infs = {}           # for keeping track of IPv4 address : interface matching
        self._m_cntrl = IPRoute()   # an interface to control traffic

    '''
    A method from the Flow_Controller interface.
    This method starts a new thread and the local
    SimpleXMLRPC server.
    '''
    def start(self):
        self._m_server.register_function(self.update_flow_parameters, 'update_flow_parameters')
        # start a new thread for handling the RPC updates
        threading.Thread(target=self._m_server.serve_forever).start()

    '''
    A way of stopping the RPC server.
    This method should usually be called when a session is done.
    '''
    def stop(self):
        # since trying stopping an object that runs on another
        # thread, an excpetion might occur
        try:
            self._m_server.shutdown() # close the server
        except RuntimeError:
            pass

    '''
    The interface that is used by a remote RL server to pass
    traffic engineering paramters to this server.
    This method handles all traffic updates accordingly to
    the passed params.
    '''

    def update_flow_parameters(self, params):
        if(len(params) != Traffic_Controller.__ACTION_TUPLE_LENGTH):
            # invalid update
            raise RuntimeError("Invalid update tuple")

        # get the updates
        (ip_address, priority, rate) = params

        if_idx = -1
        # check whether it is needed to retrieve the interface index
        if ip_address[0] in self._m_infs:
            if_idx = self._m_infs[ip_address[0]] # retireve interface index
        else:
            # find the interface that matches the ip address
            interfaces = self._m_cntrl.get_addr(family=socket.AF_INET)
            for infc in interfaces:
                # if the interface was found
                if infc.get_attr('IFA_ADDRESS') == ip_address[0]:
                    if_idx = infc['index']
                    self._m_infs[ip_address[0]] = if_idx # cache the interface
                    break # no need to process further

            # check if the ip address matched any physical interface
            if if_idx == -1:  # do nothing
                raise RuntimeError("Invalid interface")

            # apply update scheduling rules
            self._update_traffic_flow(if_idx, params)

    '''
    Helper method that uses the tc command to
    update the traffic engineering parameters.
    For further information, please refer to the
    tc command manual and the pyroute2 documentation.
    '''
    def _update_traffic_flow(self, if_idx, params):
        pass



