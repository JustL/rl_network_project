'''
  This is an interface used for handling flows in the system's
  mediator classi (Flow_Mediator class). Each of the Flow_Handlers is a
  separate process that represents a flow. The number of flows/processes
  is determined in the Flow_Mediator class.

  It is worth mentoning that a completed flow is the one that is not flowing now. Sleeping
  Waiting flows are the rest (flowing at the moment). These two statemetns are important
  as they determine the states at the reinforcement learning server.

'''

from GS_timing import micros # for precise time measurements
from flow_impl import RL_Compl_Flow
from interface_dir.flow_interfaces import WAIT_FLOW_VALID, WAIT_FLOW_INVALID

from multiprocessing import Process
from socket import AF_INET, SOCK_STREAM, IPPROTO_TCP, SOL_SOCKET
import time
import sys

# below are C strucutres that should only be used on Linux
# machines
import ctypes
from sock_addr_struct import Sockaddr_In


# global constants used among a few modules
PROTOCOL_SIGNAL = ("s", "r")      # a tuple of flags that terminate a
                                  # sending flow and a receiving flow.
                                  # In other words, each flow from
                                  # Flow_Handler is terminated by
                                  # PROTOCOL_SIGNAL[0] while each flow
                                  # from a remote server is terminated by
                                  # PROTOCOL_SIGNAL[1].

SO_PRIORITY = 12                  # a Linux flag that enables setting a
                                  # socket priority
                                  # (refer to setsockopt(7) Linux)

class Flow_Handler(Process):
    __release_version = 1
    __CONST_TIME_VAL = 3 # 3 s of sleeping


    def __init__(self, ip_address,  cmp_queue, inc_arr, flow_size, flow_pref_rate, flow_index, flow_priority=0):
        super(Flow_Handler, self).__init__()

        self._m_rem_addr = ip_address        # the ipv4 address of a remote server (including the port number)
        self._m_queue = cmp_queue            # queue for passing completed flows
        self._m_arr = inc_arr                # for storing incomplete flows
        self._m_size = flow_size             # the size for this instance of the Flow_Handler class
        self._m_rate = flow_pref_rate        # required flow rate for this flow
        self._m_index = flow_index           # the index of this flow in the incomplete flows array
        self._m_priority = ctypes.c_int(flow_priority)   # Linux stuff

    def run(self):
        # below is a C-type code that can only work on Linux
        # machines. If this process is run on any other machine,
        # the process just terminates
        if not sys.platform.startswith("linux"):
            # not a Linux machine --> return
            return

        # below code is actually C code and some Linux system calls

        # load the C standard library and the Linux system calls
        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
        except :
             # no such library
             print "'libc.so.6' could not be loaded"
             return

        # try to create a socket
        sockfd = libc.socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)

        if sockfd < 0:
            print "A new socket cannot be created"
            return

        # keep referece to the socket
        self._m_socket = sockfd

        # try to set the priority for this new socket
        if libc.setsockopt(sockfd, SOL_SOCKET,
                           SO_PRIORITY, ctypes.byref
                           (self._m_priority), ctypes.sizeof
                           (self._m_priority)) < 0:
            print "The priority of the newly created socket",
            print "cannot be modified"
            libc.close(sockfd) # close socket
            return

        # a new socket hass been created and assigmed with a priority
        # start working with the server address

        # strucutres that are used by Unix systems are used
        # for the server address
        serv_addr = Sockaddr_In()
        libc.memset(ctypes.byref(serv_addr), 0, ctypes.sizeof(serv_addr))

        # start initializeing the address structure
        serv_addr.sin_family = ctypes.c_short(AF_INET)
        serv_addr.sin_addr.s_addr = libc.inet_addr(self._m_rem_addr[0]) # a tuple -- ip a string
        serv_addr.sin_port = libc.htons(ctypes.c_ushort(self._m_rem_addr[1]))  # a tuple -- port is an integer

        # done with the server address
        # It is time to try to connect
        if libc.connect(sockfd, ctypes.byref(serv_addr),
                        ctypes.sizeof(serv_addr)) < 0:
            print "Socket could not connect to a remote server"
            libc.close(sockfd)  # close socket first
            return

        # the below code generates a flow and keeps statistics about it.
        self._flow_data(sockfd, libc)


    '''
    A helper method that registers a starting/flwoing flow.
    '''
    def _register_for_flow(self):
        attr = (self._m_size, self._m_priority, self._m_rate)  # create a tuple and pass it to the shared waiting flow array
        self._m_arr[self._m_index].set_attributes(attr)
        self._m_arr[self._m_index].set_valid(WAIT_FLOW_VALID)   # waiting flow

    '''
    Method notifies the Flow_Medaitor that the flow has completed
    '''
    def _unregister_for_flow(self, flow_cmpl_time):
        self._m_arr[self._m_index].set_valid(WAIT_FLOW_INVALID) # unvalid field
        self._m_queue.put(RL_Compl_Flow(flow_cmpl_time, self._m_size, self._m_priority, self._m_rate))# flow has been completed



    '''
    A helper method that handles the flow -- flow management

    Args:
         sockfd : socket descriptor as it is on Linux systems
         libc   : reference to the C standard lib and Linux system calls
    '''
    def _flow_data(self, sockfd, libc):

      data = (ctypes.c_char*self._m_size)()     # a flow-size string
      data[0::1] = "0"*self._m_size
      CHUNK_SIZE = 2048
      chunk = (ctypes.c_char*CHUNK_SIZE)()      # a buffer to store
                                                # received data

      # initialize some message constants
      MSG_LEN = len(PROTOCOL_SIGNAL[0])
      TERM_MSG = (ctypes.c_char*MSG_LEN)()
      TERM_MSG[0::1] = PROTOCOL_SIGNAL[0]

      # initialize some variables for receiving a flow
      RECV_SIGN = PROTOCOL_SIGNAL[1]
      RECV_LEN  = len(PROTOCOL_SIGNAL[1]) # for initializing arrays


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
          recv_data = "0"*RECV_LEN


          flow_start = micros() # get the current time for timestamping

          while total_sent < self._m_size: # send the entire flow
              sent_bytes = libc.send(sockfd, data[total_sent::1],
                      self._m_size, 0)
              if sent_bytes  < 0:
                  print "socket connection broken"
                  libc.close(sockfd) # close socket
                  return

              total_sent += sent_bytes # update sent bytes by the
                                       # number of sent bytes


          # the flow data has been sent
          # add the terminal sequence
          total_sent = 0

          while total_sent < MSG_LEN:
              sent_bytes = libc.send(sockfd, TERM_MSG[total_sent::1],
                      MSG_LEN, 0)

              if sent_bytes < 0:
                  print "socket connection broken"
                  libc.close(sockfd) # close socket
                  return

              total_sent += sent_bytes   # update counter


          print "Flow_Handler: Sent message. Waiting for response..."

          # wait for response from the remote server
          while recv_data != RECV_SIGN:   # loop until the terminal
                                          # message has been received
              read_bytes = libc.recv(sockfd, chunk, CHUNK_SIZE, 0)

              if read_bytes < 0:
                  print "socket connection broken"
                  libc.close(sockfd) # close socket
                  return

              # update the received data
              if read_bytes >= RECV_LEN:
                  recv_data = chunk[read_bytes-RECV_LEN:read_bytes:1]

              else:
                  start_idx = RECV_LEN - read_bytes
                  recv_data = chunk[0:read_bytes:1] + recv_data[start_idx::1]



          flow_end = micros() # end of the flow

          print "Flow_Handler: Received a reponse. A flow finished!!!"

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
        libc = None

        # load the linux system calls
        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)

            libc.close(self._m_socket) # close socket
        except:
            pass


    '''
    Method just addds an extra step: closing the socket.
    Basically, the same implementation as of the Process class.
    '''
    def terminate(self):
        # close the socket first
        self._close_socket()
        super(self).terminate()



















