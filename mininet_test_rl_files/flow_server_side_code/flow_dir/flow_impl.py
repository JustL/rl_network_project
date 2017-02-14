'''
This file contains the first implementations of
completed and waiting flows. The concrete classes
inherit from the flow interfaces so that
the implementation could be easily changed without
messing up with the Flow_Mediator and Flow_Handler
classes.
'''


from  interface_dir.flow_interfaces import Wait_Flow, Compl_Flow
from  interface_dir.flow_interfaces import WAIT_FLOW_VALID


from ctypes import c_int, c_double, c_short

class RL_Wait_Flow(Wait_Flow):
    '''
    Fields store the tuples used to describe a
    waiting flow. In this version, no flow tuples
    are used since it is assumed that the RL deep
    neural net should not use them as features.
    '''
    _fields_ = [('_size', c_int), ('_priority', c_int), ('_rate_limit', c_double), ('_valid_field', c_short)]

    '''
    Method returns a tuple of the waiting flow
    features that might be used for learning --
    observed state.
    '''
    def get_attributes(self):
        return (self._size, self._priority, self._rate_limit)


    '''
    Method is used to set the attributes/features
    of a waiting flow.

    parameter : must be a Python tuple
    '''
    def set_attributes(self, attr):
        self._size, self._priority, self._rate_limit = attr


    '''
    Method is used to know if this structure represents
    a waiting flow.

    returns : 1 for valid, 0 for invalid
    '''
    def is_valid(self):
        return (self._valid_field == WAIT_FLOW_VALID)


    '''
    Method sets a flow to be waiting/finished(running)

    parameter : val : 0 for invalid, any other val for
    valid
    '''
    def set_valid(self, val):
        self._valid_field = val


class RL_Compl_Flow(Compl_Flow):
    '''
    Class has a similar function as
    the above class only that stores
    completed flows.
    '''

    def __init__(self, fct=0, size=0, priority=1, rate_limit=0):
        super(RL_Compl_Flow, self).__init__()
        self._fct = fct                # flow completion time
        self._size = size              # flow size (bytes)
        self._priority = priority      # flow priority
        self._rate_limit = rate_limit  # flow rate_limit


    '''
    Method returns a tuple of a completed flow.
    '''
    def get_attributes(self):
        return (self._fct, self._size, self._priority, self._rate_limit)


    '''
    Method gives an opportunity to update
    flow tuples

    paramters : attr : must be a Python tuple
    '''
    def set_attributes(self, attr):
        self._fct, self._size, self._priority. self._rate_limit = attr


