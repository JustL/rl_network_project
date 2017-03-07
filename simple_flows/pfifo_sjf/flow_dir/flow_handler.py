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


from multiprocessing import Process
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



# constants/paramters for assigning priorities for
# generated flows
LOWER_CDF_PARAM = (1.0 / 3.0)
UPPER_CDF_PARAM = (2.0 / 3.0)


'''
Structure used for scheduling flows into
Linux priority queue bands.
'''
class CDF_Info(ctypes.Structure):
    _fields_ = [("cdf_min", ctypes.c_long),
               ("cdf_avg", ctypes.c_long),
               ("cdf_max", ctypes.c_long)]



class Flow_Handler(Process):
    __FLOW_PRIORITIES = {"default" :   0,
                         "low"     :   2,
                         "high"    :   6
                        }          # Linux puts 0th prio in 1st band,
                                   # 2's prio in 2nd band
                                   # 6th prio in 0th band

    def __init__(self, ip_address, flow_gen, data_file,
            flow_index, host_index, cdf_sch):
        super(Flow_Handler, self).__init__()



        self._init_io(flow_gen, data_file,
                host_index, flow_index)      # initialize ong related
                                             # to io

        self._m_gen        = flow_gen

        self._m_host_index = host_index      # for mininet to identify
                                             # different hosts

        self._m_close    = True              # socket needs to be closed

        self._m_rem_addr = ip_address        # the ipv4 address
                                             # of a remote server
                                             # (including the port number)


        self._m_index = flow_index           # the index of this
                                             # in a host


        self._m_shared_info = cdf_sch        # shared value that
                                             # help handle
                                             # priorities




    '''
    A helper function that reads a file and initializes the passed
    flow generator. Also, it handles so other io operations.

    Args:
        flow_gen : flow generator object
        cdf_file : a file that stores a distribution

    Might throw IOError, ValueError
    '''
    def _init_io(self, flow_gen, cdf_file, host_index, f_idx):

        flow_gen.load_cdf(cdf_file)

        with open("flow_statistics_{0}/simple_flow_{1}.csv".format(host_index, f_idx),
                "a") as fd:
            # write titles of the data columns
            fd.write("FLOW_SIZE_bytes,FCT_us\n")

        # calculate the average of the passed CDF
        self._m_cdf_avg = long(flow_gen.avg_cdf())


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

        default_prio = ctypes.c_int(Flow_Handler.__FLOW_PRIORITIES["default"])

        if libc.setsockopt(sockfd, SOL_SOCKET,
                           SO_PRIORITY, ctypes.byref(default_prio),
                           ctypes.sizeof(default_prio)) < 0:
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
        serv_addr.sin_addr.s_addr = libc.inet_addr(self._m_rem_addr[0]) # a tuple -- ip a string
        serv_addr.sin_port = libc.htons(self._m_rem_addr[1])  # a tuple -- port is an integer

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
    Method writes an FCT entry into a file.

    Args:
        flow_cmpl_time : flow completion time in us
        flow_size      : flow size in bytes
    '''
    def _record_fct(self, flow_cmpl_time, flow_size):
        # save flow completion time
        with  open("flow_statistics_{0}/simple_flow_{1}.csv".format(
            self._m_host_index, self._m_index), "a") as file_d:

            file_d.write("{0},{1}\n".format(
                    flow_size, flow_cmpl_time))



    '''
    Method does flow scheduling. The method takes the size of
    a flow and gives it a priority such that Shortest Jobs would
    be prioritized.

        Args:
            flow_size : the size of a flow in bytes


        return : priority for this flow by using Linux
                 priorities
    '''
    def _schedule_flow(self, flow_size):
        priority =  Flow_Handler.__FLOW_PRIORITIES["default"]

        # get access to the globally shared CDF structure
        # and determine the priority of a newly generated
        # flow

        # local variables for checking the global structure
        local_min = long(-1)
        local_max = long(-1)
        local_avg = self._m_cdf_avg

        need_update_min = False   # a flag for checking if the min value
                                  # of the structure needs to be updated

        need_update_max = False   # a flag for checking if the max value
                                  # needs to be updated


        # get access to global struct and read some values
        with self._m_shared_info.get_lock():
            local_min = long(self._m_shared_info.cdf_min)
            local_max = long(self._m_shared_info.cdf_max)


        # check for all cases
        if flow_size < local_avg:
            # either high or default priority
            if flow_size < local_min:
                local_min = flow_size
                priority = Flow_Handler.__FLOW_PRIORITIES["high"]
                need_update_min = True

            elif flow_size <= long(
                    LOWER_CDF_PARAM*local_min + UPPER_CDF_PARAM * local_avg):
                priority = Flow_Handler.__FLOW_PRIORITIES["high"]

        else:
            # either default or low priority
            if flow_size > local_max: # largest flow observed so far
                local_max = flow_size
                priority = Flow_Handler.__FLOW_PRIORITIES["low"]
                need_update_max = True

            elif flow_size > long(
                    UPPER_CDF_PARAM * local_avg + LOWER_CDF_PARAM*local_max):
                priority = Flow_Handler.__FLOW_PRIORITIES["low"]


        # need to access the shared structure?
        if need_update_min or need_update_max:
            # needs to update the shared structure

            with self._m_shared_info.get_lock():

                # min needs to be updated
                if need_update_min and flow_size < long(
                        self._m_shared_info.cdf_min):
                    self._m_shared_info.cdf_min = flow_size

                # max needs to be updated
                if need_update_max and flow_size > long(
                        self._m_shared_info.cdf_max):
                    self._m_shared_info.cdf_max = flow_size



        return priority


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

        # socket priority
        cur_priority = ctypes.c_int(Flow_Handler.__FLOW_PRIORITIES["default"])


        '''
        The while loop acts as if it was a server loop -- runs forever.
        This approach used for using the same socket for sending a flow
        in order to reduce overhead for creating a new socket and a new
        process. Once the flow has completed, the prcess sleeps for a
        random period of time generetated by generator.
        '''
        while 1:

            flow_size = long(self._m_gen.gen_random_cdf())
            # schedule this flow according to its size
            temp_priority = self._schedule_flow(flow_size)

            # need to change flow priority
            if temp_priority != cur_priority.value:
                # using native C int
                cur_priority.value = temp_priority

                # set priority
                if libc.setsockopt(sockfd, SOL_SOCKET,
                        SO_PRIORITY, ctypes.byref(cur_priority),
                        ctypes.sizeof(cur_priority)) < 0:
                    print "The priority of a socket cannot",
                    print "be modified at run time\n"

                    if self._m_close:
                        libc.shutdown(sockfd, SHUT_RDWR)
                        libc.close(sockfd) # close socket
                        self._m_close = False

                    return


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
            self._record_fct((flow_end - flow_start), flow_size)


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



















