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
from GS_timing import delayMicroseconds

from no_prior_info_impl import RL_Done_Flow
from interface_dir.flow_interfaces import WAIT_FLOW_VALID, WAIT_FLOW_INVALID

from multiprocessing import Process
import Queue
from socket import AF_INET
from socket import SOCK_STREAM
from socket import IPPROTO_TCP
from socket import SOL_SOCKET
from socket import SHUT_RDWR
import sys
import random


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
    __CONST_TIME_VAL =  3 # 3 s of sleeping


    def __init__(self, ip_address, cmp_queue, inc_arr,
            flow_gen, cdf_file, host_index,
            flow_index,flow_priority=0):
        super(Flow_Handler, self).__init__()



        self._init_io(flow_gen, cdf_file,
                host_index, flow_index)      # initialize IO
                                             # related vars

        self._m_gen        = flow_gen

        self._m_close    = True              # socket needs to be closed

        self._m_rem_addr = ip_address        # the ipv4 address
                                             # of a remote server
                                             # (including the port number)


        self._m_queue = cmp_queue            # queue for passing
                                             # completed flows

        self._m_arr = inc_arr                # for storing incomplete
                                             # flows


        self._m_host  = host_index           # host index
        self._m_index = flow_index           # the index of this
                                             # flow in the incomplete
                                             # flows array
        self._m_priority = ctypes.c_int(flow_priority)   # Linux stuff

        # below C types are used to represent
        # the 5 tuples of a flow
        self._m_src_ip    =   None
        self._m_src_port  =   None
        self._m_dst_ip    =   None
        self._m_dst_port  =   None



    '''
    A helper function that reads a file and initializes the passed
    flow generator. Also, it handles so other io operations.

    Args:
        flow_gen : flow generator object
        cdf_file : a file that stores a distribution
        h_idx    : host index (which server)
        f_idx    : flow index within a particular host

    Might throw IOError, ValueError
    '''
    def _init_io(self, flow_gen, cdf_file, h_idx, f_idx):

        flow_gen.load_cdf(cdf_file)

        with open("flow_statistics_{0}/simple_flow_{1}.csv".format(
            h_idx, f_idx), "a") as fd:

            # write titles of the data columns
            fd.write("FLOW_SIZE_bytes,FCT_us\n")


    def run(self):

        print "Flow_Handler: Flow index: %i" % (self._m_index,)

        random.seed(a=None) # initialize seed for the gen

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
        serv_addr.sin_family = AF_INET
        if libc.inet_aton(self._m_rem_addr[0],
                ctypes.byref(serv_addr.sin_addr)) == 0:
            print "Invalid address in 'inet_aton'"
            libc.close(sockfd)
            return

        serv_addr.sin_port = libc.htons(self._m_rem_addr[1])  # a tuple -- port is an integer

        # done with the server address
        # It is time to try to connect
        if libc.connect(sockfd, ctypes.byref(serv_addr),
                        ctypes.sizeof(serv_addr)) < 0:
            print "Socket could not connect to a remote server"
            libc.close(sockfd)  # close socket first
            return
        # a new connection has been successfully established
        # now can read types of sockets
        self._m_dst_ip = ctypes.c_uint32(
                libc.inet_addr(self._m_rem_addr[0]))
        self._m_dst_port = ctypes.c_uint16(
                libc.htons(self._m_rem_addr[1]))


        # get local address
        local_addr = Sockaddr_In()
        libc.memset(ctypes.byref(local_addr), 0,
                ctypes.sizeof(local_addr))

        sock_addr_len = ctypes.c_size_t(ctypes.sizeof(local_addr))

        # retrieve local socket address
        if libc.getsockname(sockfd, ctypes.byref(local_addr),
                ctypes.byref(sock_addr_len)) < 0:
            print "Error retrieving local socket address"
            libc.close(sockfd)
            return

        self._m_src_ip = ctypes.c_uint32(local_addr.sin_addr.s_addr)
        self._m_src_port = ctypes.c_uint16(local_addr.sin_port)

        # the below code generates a flow and keeps statistics about it.
        self._flow_data(sockfd, libc)


    '''
    A helper method that registers a starting/flowing flow.
    '''
    def _register_for_flow(self):

        # create a dictionary of items for
        # setting flows
        attrs = {}
        attrs["src_ip"]   =  self._m_src_ip.value
        attrs["src_port"] =  self._m_src_port.value
        attrs["dst_ip"]   =  self._m_dst_ip.value
        attrs["dst_port"] =  self._m_dst_port.value
        attrs["protocol"] =  IPPROTO_TCP # tcp no
        attrs["priority"] =  self._m_priority.value

        # create a tuple and pass it to the shared waiting flow array

        self._m_arr[self._m_index].set_attributes(attrs)
        self._m_arr[self._m_index].set_valid(WAIT_FLOW_VALID)
                                                # waiting flow

    '''
    Method notifies the Flow_Medaitor that the flow has completed
    '''
    def _unregister_for_flow(self, flow_cmpl_time, flow_size):
        # mark this flow as completed, not running one
        self._m_arr[self._m_index].set_valid(WAIT_FLOW_INVALID)


        try:
            self._m_queue.put(RL_Done_Flow(
                src_ip=self._m_src_ip.value,
                src_port=self._m_src_port.value,
                dst_ip=self._m_dst_ip.value,
                dst_port=self._m_dst_port.value,
                protocol=IPPROTO_TCP,
                priority=self._m_priority.value,
                fct=float(flow_cmpl_time)), block=False)
                # a flow has been completed

        except Queue.Full:
            # try to remove the first flow and
            # add this flow since it is more up-to-date

            try:
                self._m_queue.get(block=False) # remove one item

                self._m_queue.put(RL_Done_Flow(
                    src_ip=self._m_src_ip.value,
                    src_port=self._m_src_port.value,
                    dst_ip=self._m_dst_ip.value,
                    dst_port=self._m_dst_port.value,
                    protocol=IPPROTO_TCP,
                    priority=self._m_priority.value,
                    fct=float(flow_cmpl_time)), block=False) # try add
                                                      # a new one

            except Queue.Empty: # possible to add a flow
                try:
                    self._m_queue.put(RL_Done_Flow(
                        src_ip=self._m_src_ip.value,
                        src_port=self._m_src_port.value,
                        dst_ip=self._m_dst_ip.value,
                        dst_port=self._m_dst_port.value,
                        protocol=IPPROTO_TCP,
                        priority=self._m_priority.value,
                        fct=float(flow_cmpl_time)), block=False)

                except Queue.Full:
                    pass # ignore since some other processes have
                         # appended their newly completed flows


            except Queue.Full:
                pass # don't care since it means that some other
                     # process has successfully appended
                     # a newly completed flow


        finally:
            # save flow completion time
            with  open(
                    "flow_statistics_{0}/simple_flow_{1}.csv".format(
                    self._m_host, self._m_index), "a") as file_d:

                file_d.write("{0},{1}\n".format(
                    flow_size, flow_cmpl_time))



    '''
    A helper method that handles the flow -- flow management

    Args:
         sockfd : socket descriptor as it is on Linux systems
         libc   : reference to the C standard lib and Linux system calls
    '''
    def _flow_data(self, sockfd, libc):

        CHUNK_SIZE = 1024
        chunk = (ctypes.c_char*CHUNK_SIZE)()    # a buffer to store
                                                # received data

        # initialize some message constants
        MSG_LEN = len(PROTOCOL_SIGNAL[0])
        TERM_MSG = (ctypes.c_char*MSG_LEN)()
        TERM_MSG[0::1] = PROTOCOL_SIGNAL[0]

        # initialize some variables for receiving a flow
        RECV_MSG = PROTOCOL_SIGNAL[1]



        '''
        The while loop acts as if it was a server loop -- runs forever.
        This approach used for using the same socket for sending a flow
        in order to reduce overhead for creating a new socket and a new
        process. Once the flow has completed, the prcess sleeps for a
        random period of time generetated by generator.
        '''
        while 1:

            # flow size is tested with both int and long
            # keep statistics of both versions
            flow_size = int(self._m_gen.gen_random_cdf())


            self._register_for_flow() # starting a new flow
            data = (ctypes.c_char*flow_size)()
            data = "o"*flow_size


            # initialize some variables for sending a flow
            total_sent = 0


            flow_start = micros() # get the current time for timestamping

            while total_sent < flow_size: # send the entire flow
                sent_bytes = libc.send(sockfd, data[total_sent::1],
                        flow_size, 0)
                if sent_bytes  <= 0:
                    print "Socket connection  broken or closed"
                    if  self._m_close:
                        libc.shutdwon(sockfd, SHUT_RDWR)
                        libc.close(sockfd) # close socket
                        self._m_close = False
                    return


                total_sent += sent_bytes # update sent bytes by the
                                         # number of sent bytes



            # the flow data has been sent
            # add the terminal sequence
            total_sent = 0


            while total_sent < MSG_LEN:
                sent_bytes = libc.send(sockfd, TERM_MSG[total_sent::1],
                        MSG_LEN, 0)

                if sent_bytes <= 0:
                    print "Socket connection broken or closed"
                    if self._m_close:
                        libc.shutdown(sockfd, SHUT_RDWR)
                        libc.close(sockfd) # close socket
                        self._m_close = False
                    return

                total_sent += sent_bytes   # update counter


            # wait for response from the remote server

            while 1:   # loop until the terminal
                       # message has been received

                read_bytes = libc.recv(sockfd,
                        ctypes.byref(chunk), CHUNK_SIZE, 0)

                if read_bytes <= 0:
                    print "Socket connection broken or closed"
                    if self._m_close:
                        libc.shutdown(sockfd, SHUT_RDWR)
                        libc.close(sockfd) # close socket
                        self._m_close = False
                    return

                # check for received data
                if chunk[read_bytes-1] == RECV_MSG:
                    break


            flow_end = micros() # end of the flow

            # notify the flow mediator that this flow has finished
            self._unregister_for_flow((flow_end - flow_start), flow_size)


            # sleep for a random period of time
            delayMicroseconds(self._m_gen.gen_random_interval())




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
            if self._m_close: # socket has not been closed
                              # before
                libc.shutdown(self._m_socket, SHUT_RDWR)
                libc.close(self._m_socket) # close socket
                self._m_close = False
        except:
            pass


    '''
    Method just addds an extra step: closing the socket.
    Basically, the same implementation as of the Process class.
    '''
    def terminate(self):
        # close the socket first
        self._close_socket()
        super(Flow_Handler, self).terminate()



















