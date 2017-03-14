'''
This file contains an implementation of
completed and running flows. This implementation
does not require a flow to state its size in bytes
but only uses five tuples for representing a flow.
The implementation is considred to be as a more
realitic approach to flow scheduling since it
does not use prior knoweledge of the size of
a flow.
'''


from interface_dir.flow_interfaces import Wait_Flow
from interface_dir.flow_interfaces import Compl_Flow
from interface_dir.flow_interfaces import WAIT_FLOW_VALID

from ctypes import c_int, c_uint32, c_uint16, c_uint8, c_short


class RL_Run_Flow(Wait_Flow):
    '''
    Class for representing a currently running flow.
    In other words, an instance of this class is a
    flow that is currently sending some data to a
    remote server. Used for representing the state
    of the local host/server.
    '''

    _fields_ = [('_src_ip', c_uint32), ('_src_port', c_uint16),
            ('_dst_ip', c_uint32), ('_dst_port', c_uint16),
            ('_protocol', c_uint8), ('_priority', c_int),
            ('_valid_field', c_short)]

    '''
    Method returns a tuple of the waiting flow
    features that might be used for learning --
    observed state.
    '''
    def get_attributes(self):
        return (long(self._src_ip),  int(self._src_port),
                long(self._dst_ip),  int(self._dst_port),
                int(self._protocol), int(self._priority))

    '''
    Method is used for setting attributes/features
    of such a flow.
    '''
    def set_attributes(self, attrs):

        if not attrs:
            return


        if  'src_ip' in attrs:
            self._src_ip     =   c_uint32(attrs['src_ip'])


        if 'src_port' in attrs:
            self._src_port   =   c_uint16(attrs['src_port'])


        if 'dst_ip' in attrs:
            self._dst_ip     =   c_uint32(attrs['dst_ip'])


        if 'dst_port' in attrs:
            self._dst_port   =   c_uint16(attrs['dst_port'])


        if 'protocol' in attrs:
            self._protocol   =   c_uint8(attrs['protocol'])


        if 'priority' in attrs:
            self._priority   =   c_int(attrs['priority'])


    '''
    Method used for determining if this intance of
    a flow is a running/active flow.
    '''
    def is_valid(self):
        return (self._valid_field == WAIT_FLOW_VALID)



    '''
    Method for setting the validity of a flow --
    either active or inactive.

    Args:
        val : a value from the flow_interfaces module
    '''
    def set_valid(self, val):
        self._valid_field = val


class RL_Done_Flow(Compl_Flow):
    '''
    Class has a similar function as
    the above class only that this
    class represents completed flows.
    '''

    def __init__(self, src_ip, src_port, dst_ip, dst_port,
            protocol, priority, fct):
        super(RL_Done_Flow, self).__init__()

        self._m_src_ip     =   src_ip    # source ip
        self._m_src_port   =   src_port  # source port

        self._m_dst_ip     =   dst_ip    # ip address of the destination
        self._m_dst_port   =   dst_port  # destination port number

        self._m_protocol   =   protocol  # protocol number
                                         # usually TCP number

        self._m_priority   =   priority  # flow priority
        self._m_fct        =   fct       # flow completion time


    '''
    Method for retrieving the representation
    of this flow
    '''
    def get_attributes(self):
        return (self._m_src_ip,   self._m_src_port,
                self._m_dst_ip,   self._m_dst_port,
                self._m_protocol, self._m_priority,
                self._m_fct)


    '''
    Method for setting/updating an instance of
    the RL_Done_Flow.

    Args:
        attrs : attributes for updating a flow
    '''
    def set_attributes(self, attrs):
        # update attributes by using
        # the passed values
        if not attrs:
            return

        self._m_src_ip     =   attrs.get('src_ip', self._m_src_ip)
        self._m_src_port   =   attrs.get('src_port', self._m_src_port)

        self._m_dst_ip     =   attrs.get('dst_ip', self._m_dst_ip)
        self._m_dst_port   =   attrs.get('dst_port', self._m_dst_port)


        self._m_protocol   =   attrs.get('protocol', self._m_protocol)
        self._m_priority   =   attrs.get('priority', self._m_priority)
        self._m_fct        =   attrs.get('fct', self._m_fct)

