'''
This file contains a simple server that handles the sent flows
from remote servers and sends a simple response (PROTOCOL_SIGNAL[1]).
It is worht mentioning that this class has to choose between threading
multiprocessing. Since it was found that multiprocessing is a
better option in order to run in parallel in Python, this option
is chosen. However, knowing that mutiprocessing is a very resourcee-intensive approach, multithreading should me tested if the performance
of this server is pretty bad.
'''

# import the protocol
from flow_handler import PROTOCOL_SIGNAL, SO_PRIORITY
from sock_addr_struct import Sockaddr_In

from multiprocessing import Process
from socket import AF_INET, SOCK_STREAM, IPPROTO_TCP, SOL_SOCKET
import ctypes # for using native C data structures
import sys


'''
This function is used by a separate process to
run a connection. Since the function runs in a
separate process, the libc has to be re;oaded again
'''
def sock_proc(client):

    # try to load the standard C library and the Linux sys calls
    libc = None
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
    except Exception:
        return   # terminate this process

    # have loaded the C lib and sys calls, also have a ref to a socket
    # send all replies with a high priority (even if it is not supported)
    # don't check for the status number
    priority = ctypes.c_int(Simple_Flow_Server.REPLY_PRIORITY)
    libc.setsockopt(client, SOL_SOCKET, SO_PRIORITY,
            ctypes.byref(priority), ctypes.sizeof(priority))

    # run a connection
    # since this is a server process, it always waits for a client's
    # request before it takes any actions
    REPLY_LEN       = len(PROTOCOL_SIGNAL[1])  # terminal signal length
    REPLY_MSG       = (ctypes.c_char*(REPLY_LEN + 1))()
    REPLY_MSG.value = PROTOCOL_SIGNAL[1]       # a terminal sequence

    RECV_LEN        = len(PROTOCOL_SIGNAL[0])  # length of client's term signal
    RECV_MSG        = PROTOCOL_SIGNAL[0]       # terminal message
    MAX_READ        = 2048                     # at most that many bytes to read
                                               # in one socket call

    try:
        while 1: # run forever
            recv_data = [] # where data is stored
            chunk = (ctypes.c_char*MAX_READ)()

            while 1:
                # since the teminal sequence must be at the end of the flow
                # check only the last items of the received data
                read_bytes = libc.recv(client, chunk, MAX_READ-1, 0)

                if read_bytes < 0:
                    raise RuntimeError("socket connection broken")

                # check last bytes for the terminal msg
                if len(chunk.value) >= RECV_LEN:
                    if chunk.value[(-RECV_LEN): :1] == RECV_MSG:
                        # means the client has finished its flow -- send reply
                        break
                    # don't need to store all data -- just last few bytes
                    recv_data = chunk.value[(-RECV_LEN): :1]

                else: # check the previous data combined with the new data
                    recv_data.append(chunk)
                    if len("".join(recv_data)) >= RECV_LEN: # check for terminal sequence
                        if recv_data[(-RECV_LEN): : 1] == RECV_MSG:
                            break
                        recv_data = recv_data[(-RECV_LEN): :1] # store some va


            # the below code just sends a reply to the client and
            # waits for a new message
            total_sent = 0
            while total_sent < REPLY_LEN:
                sent_bytes = libc.send(client, REPLY_MSG[total_sent : ], REPLY_LEN, 0) #send reply
                if sent_bytes < 0:
                    raise RuntimeError("socket connection broken")
                # update the number of sent bytes
                total_sent += sent_bytes

            # done handling the flow.
            # waiting for another one.


    finally:
        pass



'''
The class just handles incoming requests/connections
and initializes processes to handle them.
The server is designated to work on only Linux machines.
'''
class Simple_Flow_Server(object):
    __LISTEN_QUEUE   = 100       # number of waiting requests to connect
    REPLY_PRIORITY = 6         # set all server priorities to
                                 # REPLY_PRIORITY so that the replies would
                                 # immediately sent back to the source server.
                                 # __REPLY_PRIORITY = HIGHEST_PRIORITY  - 1
                                 # (HIGHES_PRIORITY requires some permission)

    def __init__(self, ip_address='127.0.0.1',  port_num = 17850):
        self._m_conns = []     # an empty list of current connections
        self._m_procs = []     # an empty list of processes
        self._m_ip    = (ip_address, port_num)


        try:
            # try to bind the socket to an interface
            self._m_socket.bind((ip_address, port_num))
        except Exception:
            print 'Server failed binding its socket'
            sys.exit(-1)

        # sucessfully binded. Process further
        self._m_socket.listen(Simple_Flow_Server.__LISTEN_QUEUE)

    '''
    A public method that must be called before using
    the server. This method starts waiting/accepting new
    connections and handles them (passes to a new process/thread).
    '''
    def start_server(self):
        # this method onyl works on Linux machines
        # check for the platform
        if not sys.platform.startswith("linux"):
           # no further processing
           return

        # construct a Linux socket
        try:
            (sockfd, libc) = self._init_linux_rec()
        except Exception:
            raise

        # run forever
        try:
            while 1:
                # accept connections from other servers
                client_sock = libc.accept(sockfd, 0, 0)

                # check if nothing went wron with the client
                if client_sock < 0:
                    continue  # ignore the rest of the code

                # append the socket to the connection list
                self._m_conns.append(client_sock)

                # create a new process and append it to the list
                prc = Process(target=sock_proc, args=(client_sock, ))
                self._m_procs.append(prc)
                prc.start()

                # start over again

        finally:  # server might be interrupted by an excpetion
            self._stop_server() # close all connections

    '''
    Helper method to tear down all current connections
    and stop all running processes
    '''
    def _stop_server(self):
        # stopp all the started processes
        for prc in self._m_procs:
            prc.terminate()
            prc.join() # wait until the process stops

        # all processes have been stopped
        # close sockets
        for conn in self._m_conns:
            try:
                conn.shutdown()
                conn.close()
            except Exception:   # might raise an exception if the socket has already been closed
                pass

        # processes and sockets have been handled
        self._m_conns = None
        self._m_procs = None


    '''
     Helper function to initialize Linux system resources
     for running a TCP server.
    '''
    def _init_linux_rec(self):
        # try to load the C standard library and the Linux system calls
        libc = None

        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
        except Exception:
             raise RuntimeError("'libc.so could not bea loaded'")

        # library and system calls have been loaded, use them to create
        # a TCP socket
        sockfd = libc.socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        if sockfd < 0:
           raise RuntimeError("System error: cannot create a new socket")

        m_addr = Sockaddr_In() # sock addr structure
        libc.memset(ctypes.byref(m_addr), 0, ctypes.sizeof(m_addr))

        # initialize the address struct with the passed addresses
        m_addr.sin_damily = ctypes.c_short(AF_INET)
        m_addr.sin_addr.s_addr = ctypes.c_ulong(libc.inet_addr(self._m_ip[0]))
        m_addr.sin_port = ctypes.c_ushort(libc.htons(self._m_ip[1]))

        # address structure and a socket are built, bind and start listening
        if libc.bind(sockfd, ctypes.byref(m_addr), ctypes.sizeof(m_addr)) < 0:
            raise RuntimeError("System error: cannot bind")

        if libc.listen(sockfd, Simple_Flow_Server.__LISTEN_QUEUE) < 0:
            raise RuntimeError("System error: cannot start listening")

        # done initializing the required Linux resources

        return (sockfd, libc)






