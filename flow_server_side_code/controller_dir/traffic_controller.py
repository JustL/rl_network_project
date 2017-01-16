from interface_dir.flow_controller import Flow_Controller
from SimpleXMLRPCServer import SimpleXMLRPCServer
import threading

class Traffic_Controller(Flow_Controller):
    '''
    The class is a concrete implementation of the Flow_Controller
    interface. The class runs an RPC server on a separate thread
    and handles all the requests coming from the remote RL machine.
    '''

    def __init__(self, port_num=16850):
        self._init_object(port_num)


    '''
    Helper method to initialize all the needed fields
    of this flow controller.
    '''
    def _init_object(self, port_num):
        self._m_server = SimpleXMLRPCServer(('localhost', port_num))

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
        pass

