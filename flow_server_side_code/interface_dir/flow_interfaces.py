'''
 This file contains interface for flows.
 Since there might be a few different representations of
 a waiting flow/completed flow, these interface provides
 abstractions for the implemnetations. The Flow_Mediator class uses
 references to the below interfaces.

'''

from ctypes import Structure


# some global constants for setting/checking the state
# of a running flow.
WAIT_FLOW_VALID = 1
WAIT_FLOW_INVALID = 0

'''
 An Interface for an incomplete flow.
 The derived classes implement the provided
 methods.
'''

class Wait_Flow(Structure):

    '''
    Method provides an interface
    and dedicates the implementation
    of this method for derived classes.

    return : the representation of a
             waiting flow.
    '''
    def get_attributes(self):
        pass


    '''
    Method provides an abstract setter for
    flows so that any kind of supported cstruct
    could be used.

    parameters : flow attribute(s)
    '''
    def _set_attributes(self, attr):
        pass


    '''
    Method provides an interface to check if this
    structure/flow is waiting.
    '''
    def is_valid(self):
        pass


    '''
    Method provides an interface for
    setting a flow to be a valid waiting
    flow.
    '''
    def _set_valid(self, val):
        pass


'''
 An interface for completed flows.
'''
class Compl_Flow(object):


    def __init__(self):
        pass


    '''
     Method provides an abstraction to
     represent a completed flow.

     returns : an abstraction to
               completed flows
    '''
    def get_attributes(self):
        pass

    '''
      Method provides an easy way
      to set the representation of
      a completed flow.

     paramters : flow attribute(s)
    '''
    def _set_attributes(self, attr):
        pass

