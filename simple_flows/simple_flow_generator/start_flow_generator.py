'''
This file contains the script that should be run on each of a cluster
server in order to make it manageable by a remote reinforcement server.
The script creates a server that listens on some predefined port and also
runs a program that allows this server send its traffic information to
a remote reinforcemtn learning server that processes the data and sends
a reply back to this server. This scripts can be considered as a client
in the overall architecture.
'''

import threading
import signal
import sys
import Queue


# files from the project
from start_simple_server import SERVER_PORT
from controller_dir.flow_mediator import Flow_Mediator


# global flags that informs
# the program when to terminate
term_event = 1


# function is used by a newly created thread to
# run the flow mediator program
def run_flow_mediator(mediator_queue):
    flow_mediator = mediator_queue.get()
    try:
        flow_mediator.start_updating() # run the program
    except:
        pass



def signal_term_handler(signal, frame):
    # notify all processes and terminate them"
    global term_event
    term_event = 0




def start_generator(ip_addrs):

    # the port number that a simple flow server listen on
    # (refer to start_simple_server.py)
    addresses = [tuple([ip_, SERVER_PORT]) for ip_ in ip_addrs]

    # register signal term
    signal.signal(signal.SIGTERM, signal_term_handler)



    # below code creates and initializes a Flow_Mediator for
    # generating workflows

    mediator = None

    # might raise an exception
    try:
        mediator = Flow_Mediator(ip_addresses=addresses)

    except:
        print "Flow Medaitor could not be instantiated"
        sys.exit(-1)


    # need to use a Queue to pass a reference to
    # a new thread
    m_queue = Queue.Queue(1)
    m_queue.put(mediator)

    flow_handler_thread = threading.Thread(target=run_flow_mediator,
            args=(m_queue,))

    flow_handler_thread.start()

    # run until this proces has to be terminated
    while term_event != 0:
        pass

    print "Flow_mediator to kill processes have to now"
    # stop the mediator
    try:
        mediator.kill_processes()
    except:
        pass

    # wait until all the started  threads are terminated
    flow_handler_thread.join()


if __name__ == "__main__":

    # first step is to check if some server addresses have
    # been passed for running
    if len(sys.argv) < 2:
        print "Please pass more arguments.",
        print "There must be at least one public ip address:"
        print "--- Remote server address(es)."
        print "(e.g.,  143.125.15.16  ...)"

    else: # run a new generator
        start_generator(sys.argv[1::1])



