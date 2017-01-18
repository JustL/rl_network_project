'''
This file contains the interface that every flow controller
should implement so that a remote server that runs a reinforcement
learning algorithm could use traffic control on this server.
The interface pwovides a few methods that are used by the remote
flow controller and the local Flow_Mediator.
'''

class Flow_Controller(object):

    '''
    An interface to start the concrete class
    running the functionality.
    '''
    def start(self):
        pass


    '''
    An interface to stop the concrete class
    running.
    '''
    def stop(self):
        pass

    '''
    An interface to retrieve the tuple that
    contains the IPv4 address of the controller.
    This interface is provided since it is preferred
    to run a controller on a separate thread/process.
    '''
    def get_controller_address(self):
        pass


    '''
    An interface to pass the computed parameters to
    a concrete traffic controller.
    Paramaters should be encapsulated into a tuple.
    '''
    def update_flow_parameters(self, pars):
        pass
