'''
  This is an interface used for handling flows in the system's
  mediator classi (Flow_Mediator class). Each of the Flow_Handlers is a
  separate process that represents a flow. The number of flows/processes
  is determined in the Flow_Mediator class.

  It is worth mentoning that a completed flow is the one that is not flowing now. Sleeping
  Waiting flows are the rest (flowing at the moment). These two statemetns are important
  as they determine the states at the reinforcement learning server.

'''

from GS_timing import micros # for a precise time measurements
from flow_impl import RL_Compl_Flow
from multiprocessing import Process
from socket import socket as Socket
from socket import AF_INET, SOCK_STREAM, IPPROTO_TCP
import socket.error
import time


class Flow_Handler(Process):
    __release_version = 1
    __CONST_TIME_VAL = 3 # 3 s of sleeping
    PROTOCOL_SIGNAL = ('s', 'r') # strings are used for notifying the remote server that a flow has completed

    def __init__(self, ip_address,  cmp_queue, inc_arr, flow_size, flow_pref_rate, flow_index, flow_priority=0):
        super.__init__(Flow_Handler, self)
        self._m_socket = None                # socket that handles the comminication
        self._m_rem_address = ip_address     # the ipv4 address of a remote server (including the port number)
        self._m_queue = cmp_queue            # queue for passing completed flows
        self._m_arr = inc_arr                # for storing incomplete flows
        self._m_size = flow_size             # the size for this instance of the Flow_Handler class
        self._m_rate = flow_pref_rate        # required flow rate for this flow
        self._m_index = flow_index           # the index of this flow in the incomplete flows array
        self._m_priority = flow_priority     # TO DO

    def run(self):

        try: # creating a socket
            self._m_socket = Socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        except socket.error as msg:
            self._m_socket = None

            print 'Could not create a socket:', msg
            return

        try: # try to connect to the remote server
            self._m_socket.connect(self._rem_address)
        except socket.error:
            self._m_socket.close()
            self._m_socket = None
            print 'Could not connect to %s:%i.' % self._m_rem_address

            return

        # the below code generates a flow and keeps statistics about it.
        self._flow_data()


    '''
    A helper method that registers a starting/flwoing flow.
    '''
    def _register_for_flow(self):
        attr = (self._m_size, self._m_priority, self._m_rate)  # create a tuple and pass it to the shared waiting flow array
        self._m_arr[self._m_index].set_attributes(attr)
        self._m_arr[self._m_index].set_valid(1)                # waiting flow

    '''
    Method notifies the Flow_Medaitor that the flow has completed
    '''
    def _unregister_for_flow(self, flow_cmpl_time):
        self._m_arr[self._m_index].set_valid(0) # unvalid field
        self._m_queue.put(RL_Compl_Flow(flow_cmpl_time, self._m_size, self._m_priority, self._m_rate))# flow has been completed

    '''
    A helper method that handles the flow -- flow management
    '''
    def _flow_data(self):

      data = '0'*self._m_size # a flow-size string

      # initialize some message constants
      MSG_LEN = len(Flow_Handler.PROTOCOL_SIGNAL[0])
      TERM_MSG = Flow_Handler.PROTOCOL_SIGNAL[0]

      # initialize some variables for receiving a flow
      RECV_LEN = len(Flow_Handler.PROTOCOL_SIGNAL[1])
      RECV_SIGN = Flow_Handler.PROTOCOL_SIGNAL[1]

      '''
      The while loop acts as if it was a server loop -- runs forever.
      This approach used for using the same socket for sending a flow in order
      to reduce overhead for creating a new socket and a new process.
      Once the flow has completed, for some fixed time the process sleeps.
      '''
      while 1:
          self._register_for_flow() # starting a new flow

          # initialize some variables for sending a flow
          total_sent = 0
          recv_data = []


          flow_start = micros() # get the current time for timestamping

          while total_sent < self._m_size: # send the entire flow
              sent_bytes = self._m_socket.send(data[total_sent : ])
              if sent_bytes  == 0:
                  raise RuntimeError("socket connection broken")
              total_sent += sent_bytes # update sent bytes by the number of sent bytes

          # the flow data has been sent
          # add the terminal sequence
          total_sent = 0

          while total_sent < MSG_LEN:
              sent_bytes = self._m_socket.send(TERM_MSG[total_sent : ])
              if sent_bytes == 0:
                  raise RuntimeError("socket connection broken")


          # wait for response from the remote server
          while "".join(recv_data) != RECV_SIGN:   # loop until the terminal message has been received
              chunk = self._m_socket.recv(RECV_LEN)

              if chunk == '':
                  raise RuntimeError("socket connection broken")
              recv_data.append(chunk)  # update the receive data


          flow_end = micros() # end of the flow

          self._unregister_for_flow((flow_end - flow_start)) # notify the flow mediator that this flow has finished

          time.sleep(Flow_Handler.__CONST_TIME_VAL)  # sleep for const time seconds


    '''
    Method closes the socket that belongs to this process.
    The rsources allocated to the socket are properly
    released and the connection terminated in an appropriate
    manner.
    '''
    def _close_socket(self):
        # close socket so that the resources would be
        # deallocated as soon as possible.
        self._m_socket.shutdown()
        self._m_socket.close()


    '''
    Method just addds an extra step: closing the socket.
    Basically, the same implementation as of the Process class.
    '''
    def terminate(self):
        # close the socket first
        self._close_socket()
        super(self).terminate()



















