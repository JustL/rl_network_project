'''
This file contains the script that has to be run on each of the cluster
server since the scripts initiliazes a simple server. This script
must be run first because servers must be started first.
'''

import threading
import Queue
import signal
import sys


# files from the project
from flow_dir.simple_flow_server import Simple_Flow_Server


# this value is referred to by other scripts
SERVER_PORT = 30150 # all servers listen on the same port

# global flag for temination
term_event = 1

# function is handled by a
# thread that starts the server application
def run_server(server_queue):
    # retrieve the server object
    server = server_queue.get()
    try:
        server.start_server()
    except:
        pass


def signal_term_handler(signal, frame):
    # modify the global flag to notify
    # the application that is has to be finished
    global term_event
    term_event = 0




if __name__ == "__main__":

    # first initialize a server that listens and
    # sends reponses to other cluster servers.
    # This server is only needed for generating a flow.

    if len(sys.argv) < 2:
        print "Please enter a public IP iddress for a flow server",
        print "(e.g., 175.159.10.14)"
        sys.exit(0)

    # register a signal handler
    signal.signal(signal.SIGTERM, signal_term_handler)

    # create a new thread and a new server
    m_queue = Queue.Queue(1)
    server = Simple_Flow_Server(ip_address=sys.argv[1],
            port_num=SERVER_PORT)
    m_queue.put(server)  # a queue is used for passing the server object

    # create a thread that runs the server
    server_thread = threading.Thread(target=run_server, args=(m_queue,))
    server_thread.start()

    # wait when term event is set
    while term_event:
        pass


    # terminate the server
    try:
        server.stop_server()
    except:
        pass

    # wait until all started threads are done
    server_thread.join()
