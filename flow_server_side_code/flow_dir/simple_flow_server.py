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
from flow_handler import PROTOCOL_SIGNAL

from multiprocessing import Process
import socket
import sys


'''
This function is used by a separate proces to
run a connection
'''
def sock_proc(client):
    # run a connection
    # since this is a server process, it always waits for a client's
    # request before it takes any actions
    REPLY_MSG = PROTOCOL_SIGNAL[1]       # a terminal sequence
    REPLY_LEN = len(PROTOCOL_SIGNAL[1])  # terminal signal length
    RECV_LEN  = len(PROTOCOL_SIGNAL[0])  # length of client's term signal
    RECV_MSG  = PROTOCOL_SIGNAL[0]       # terminal message
    MAX_READ  = 2048                     # at most that many bytes to read in one socket call

    while 1: # run forever
        recv_data = [] # where data is stored

        while 1:
            # since the teminal sequence must be at the end of the flow
            # check only the last items of the received data
            chunk = client.recv(MAX_READ)

            if chunk == '':
                raise RuntimeError("socket connection broken")

            # check last bytes for the terminal msg
            if len(chunk) >= RECV_LEN:
                if chunk[(-RECV_LEN): :1] == RECV_MSG:
                    # means the client has finished its flow -- send reply
                    break
                # don't need to store all data -- just last few bytes
                recv_data = chunk[(-RECV_LEN): :1]

            else: # check the previous data combined with the new data
                recv_data.append(chunk)
                if len(recv_data) >= RECV_LEN: # check for terminal sequence
                    if recv_data[(-RECV_LEN): : 1] == RECV_MSG:
                        break
                    recv_data = recv_data[(-RECV_LEN): :1] # store some va


        # the below code just sends a reply to the client and
        # waits for a new message
        total_sent = 0
        while total_sent < REPLY_LEN:
            sent_bytes = client.send(REPLY_MSG[total_sent : ]) #send reply
            if sent_bytes == 0:
                raise RuntimeError("socket connection broken")
            # update the number of sent bytes
            total_sent += sent_bytes

        # done handling the flow.
        # waiting fro another one.


'''
The class just handles incoming requests/connections
and initializes processes to handle them.
'''
class Simple_Flow_Server(object):
    __LISTEN_QUEUE = 100            # number of waiting requests to connect

    def __init__(self, ip_address='127.0.0.1',  port_num = 17850):
        self._m_conns = []     # an empty list of current connections
        self._m_procs = []     # an empty list of processes
        self._m_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPROTO_TCP)

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
        # run forever
        try:
            while 1:
                # accept connections from other servers
                (client_sock, address) = self._m_socket.accept()
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

            while (prc.is_alive()): # wait until the process stops
                pass

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






