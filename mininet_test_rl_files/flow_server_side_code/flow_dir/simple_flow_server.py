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

import threading
from multiprocessing import Process
from socket import AF_INET
from socket import SOCK_STREAM
from socket import IPPROTO_TCP
from socket import SOL_SOCKET
from socket import SHUT_RDWR
from socket import socket as Socket
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
    except:
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
    REPLY_LEN         = len(PROTOCOL_SIGNAL[1])     # terminal signal
                                                    # length
    REPLY_MSG         = (ctypes.c_char*REPLY_LEN)()
    REPLY_MSG[0::1]   = PROTOCOL_SIGNAL[1]          # terminal sequence

    RECV_LEN          = len(PROTOCOL_SIGNAL[0])     # length of
                                                    # client's term
                                                    # signal

    RECV_MSG          = PROTOCOL_SIGNAL[0]          # terminal message
    MAX_READ          = 2048                        # at most that many
                                                    # bytes to read
                                                    # in one socket call



    while 1: # run forever
        recv_data = "0"*RECV_LEN # where received data is stored
        chunk = (ctypes.c_char*MAX_READ)()


        while recv_data != RECV_MSG:
            # since the teminal sequence must be at the end of the flow
            # check only the last items of the received data
            read_bytes = libc.recv(client, chunk, MAX_READ, 0)

            if read_bytes <= 0:
                print "Socket connection broken or closed"
                libc.shutdown(client, SHUT_RDWR)
                libc.close(client) # close socket and terminate
                return

            # check update received data
            if read_bytes >= RECV_LEN:
                # read last bytes for checking
                recv_data = chunk[read_bytes-RECV_LEN:read_bytes:1]

            else: # check the previous data combined with the new data
                start_idx = RECV_LEN - read_bytes
                recv_data = chunk[0:read_bytes:1] + recv_data[start_idx::1]


        # the below code just sends a reply to the client and
        # waits for a new message

        total_sent = 0
        while total_sent < REPLY_LEN:
            sent_bytes = libc.send(client,
                    REPLY_MSG[total_sent:REPLY_LEN:1],
                    REPLY_LEN, 0) #send reply

            if sent_bytes <= 0:
                print "Socket connection broken or closed"
                libc.shutdown(client, SHUT_RDWR)
                libc.close(client) # close socket and terminate
                return

            # update the number of sent bytes
            total_sent += sent_bytes


    # done handling the flow.
    # waiting for another one.




'''
The class just handles incoming requests/connections
and initializes processes to handle them.
The server is designated to work on only Linux machines.
'''
class Simple_Flow_Server(object):
    __LISTEN_QUEUE   = 100       # number of waiting requests to connect
    REPLY_PRIORITY = 6           # set all server priorities to
                                 # REPLY_PRIORITY so that the replies would
                                 # immediately sent back to the source server.
                                 # __REPLY_PRIORITY = HIGHEST_PRIORITY  - 1
                                 # (HIGHES_PRIORITY requires some permission)

    def __init__(self, ip_address='127.0.0.1',  port_num = 17850):
        self._m_conns = []               # an empty list of current
                                         # connections
        self._m_procs = []               # an empty list of processes
        self._m_ip    = (ip_address, port_num)
        self._m_exit  = threading.Event() # a flag that tells the server to
                                         # keep looping
        self._m_lock = threading.Lock()  # a lock that protects data
                                         # consistency withing this program
        self._m_sockfd = None            # a socket file descriptor

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
        except:
            raise

        # run forever
        try:
            while not self._m_exit.is_set():
                # accept connections from other servers
                client_sock = libc.accept(sockfd, 0, 0)

                # check if nothing went wron with the client
                if client_sock < 0:
                    continue  # ignore the rest of the code


                # append the socket to the connection list
                # get a lock to modify the resources
                with self._m_lock:
                    if self._m_exit.is_set(): # check for the flag first
                        break

                    self._m_conns.append(client_sock)

                    # create a new process and append it to the list
                    prc = Process(target=sock_proc, args=(client_sock, ))
                    self._m_procs.append(prc)
                    prc.start()

                    # start over again

        finally:  # server might be interrupted by an internal exception
            if self._m_procs or self._m_conns:
                self.stop_server() # close all connections

    '''
    Helper method to tear down all current connections
    and stop all running processes
    '''
    def stop_server(self):

        # this method can be called from a few threads so locking is needed
        with self._m_lock:
            # load  a new referece to the Linux system calls
            # since the previous one might be used by another thread
            libc = None
            try:
                libc = ctypes.CDLL("libc.so.6", use_errno=True)
            except:
                raise RuntimeError("'libc.so.6' could not be loaded")

            self._m_exit.set()  # stop looping
            # close all connections first
            if self._m_conns:
                for conn in self._m_conns:
                    try:
                        libc.shutdown(conn, SHUT_RDWR)
                        libc.close(conn)
                    except: # an exception might be raised since closing
                        # sockets that are handled by other processes
                        pass

            # stopp all the started processes
            if self._m_procs:
                for prc in self._m_procs:
                    if prc.is_alive():
                        prc.terminate()
                        prc.join() # wait until the process stops


            # processes and sockets have been handled
            self._m_conns = None
            self._m_procs = None
            libc.close(self._m_sockfd, SHUT_RDWR)
            libc.close(self._m_sockfd) # close my own socket

            # send some data to my own socket to terminate
            # .accept system call
            socket = None

            try:
                socket = Socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
                socket.connect(self._m_ip) # this should throw an
                                           # exception
            except:
                # exception should be thrown, so handle it
                if socket:
                    socket.close()



    '''
     Helper function to initialize Linux system resources
     for running a TCP server.
    '''
    def _init_linux_rec(self):
        # try to load the C standard library and the Linux system calls
        libc = None

        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
        except:
             raise RuntimeError("'libc.so could not be loaded'")

        # library and system calls have been loaded, use them to create
        # a TCP socket
        sockfd = libc.socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        if sockfd < 0:
           raise RuntimeError("System error: cannot create a new socket")

        m_addr = Sockaddr_In() # sock addr structure
        libc.memset(ctypes.byref(m_addr), 0, ctypes.sizeof(m_addr))

        # initialize the address struct with the passed addresses
        m_addr.sin_family = AF_INET
        m_addr.sin_addr.s_addr = libc.inet_addr(self._m_ip[0])
        m_addr.sin_port = libc.htons(self._m_ip[1])

        # address structure and a socket are built, bind and start listening
        if libc.bind(sockfd, ctypes.byref(m_addr), ctypes.sizeof(m_addr)) < 0:
            raise RuntimeError("System error: cannot bind")

        if libc.listen(sockfd, Simple_Flow_Server.__LISTEN_QUEUE) < 0:
            raise RuntimeError("System error: cannot start listening")

        # done initializing the required Linux resources
        self._m_sockfd = sockfd  # for clsosing this socket later
        return (sockfd, libc)






