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
import Queue
import signal
import sys



# files from the project
from interface_dir.flow_controller import Flow_Controller
from start_simple_server import SERVER_PORT
from flow_dir.flow_impl import RL_Wait_Flow
from controller_dir.traffic_controller import Traffic_Controller
from controller_dir.flow_mediator import Flow_Mediator


# global flags that informs
# the program when to terminate
term_event = 1


# function is used by a newly created thread to
# run the flow mediator program
def run_flow_mediator(mediator_queue):
    flow_mediator = mediator_queue.get()
    flow_mediator.start_updating() # run the program



def signal_term_handler(signal, frame):
    # notify all processes and terminate them
    global term_event
    term_event = 0




if __name__ == "__main__":
    # first step is to check if some server addresses have
    # been passed for running
    if len(sys.argv) < 4:
        print "Please pass more arguments.",
        print "There must be at least three public ip addresses:"
        print "--- IPv4 of this server's interface;"
        print "--- Reinforcement learnig server address;"
        print "--- Remote server address(es)."
        print "(e.g., 175.2.11.123  143.125.15.13  143.125.15.16  ...)"
        sys.exit(0)


    RL_SERVER_PORT = 32202 # the reinforcement server must listen on this port number (refer to rl_server_side_code/rl_server_dir)
    # get addresses (reinforcemtn learning server, other servers)
    rl_server_addr = (sys.argv[2], RL_SERVER_PORT)

    # the port number that a simple flow server listen on (refer to start_simple_server.py)
    addresses = [tuple([sys.argv[idx], SERVER_PORT]) for idx in xrange(3, len(sys.argv), 1)]

    # register signal term
    signal.signal(signal.SIGTERM, signal_term_handler)


    # below code creates and initializes a Flow_Mediator for
    # generating workflows

    wait_flow_type = RL_Wait_Flow()  # determines a C array's type
    con = Traffic_Controller((sys.argv[1],
        Flow_Controller.CONTROLLER_PORT_NUM))
    mediator = None

    # might raise an exception
    try:
        mediator = Flow_Mediator(rl_server=rl_server_addr,
                      ip_addresses=addresses,
                      controller=con,
                      wf_type=wait_flow_type)

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
    while term_event:
        pass

    # stop the mediator
    try:
        mediator.kill_processes()
    except:
        pass

    # wait until all the started  threads are terminated
    flow_handler_thread.join()
