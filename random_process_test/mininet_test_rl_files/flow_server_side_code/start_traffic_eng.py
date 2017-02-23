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

from flow_generator.factories.poisson_flow_generator_factory import Poisson_Generator_Factory


# global flags that informs
# the program when to terminate
term_event = 1


# function is used by a newly created thread to
# run the flow mediator program
def run_flow_mediator(mediator_queue):
    flow_mediator = mediator_queue.get()
    flow_mediator.start_updating() # run the program



def signal_term_handler(signal, frame):
    # notify all processes and terminate them"
    global term_event
    term_event = 0



'''
Function returns a mapping from the
passed string to a Python dictionary.
'''
def _convert_into_dict(enc_string):

    result_dict = {}

    sep_items = "//"     # extracts items of a dict
    sep_key_val = "::"   # separates the key and the value

    if enc_string[-len(sep_items)::1] == sep_items:
        enc_string = enc_string[0:-len(sep_items):1] # discard last
                                                     # separator

    items = enc_string.split(sep_items)


    # loop through items and
    # put them in the dictionary

    for item in items:
        prop_dict_tuple = item.split(sep_key_val)

        # add an item to the result dictionary
        result_dict[prop_dict_tuple[0]] = prop_dict_tuple[1]


    return result_dict




def main(dist_file, host, host_infcs,
        rl_server_ip, remote_ips):


    RL_SERVER_PORT = 32202
    # the reinforcement server must
    # listen on this port number
    # (refer to rl_server_side_code/rl_server_dir)
    # get addresses
    # (reinforcemtn learning server, other servers)
    rl_server_addr = (rl_server_ip, RL_SERVER_PORT)

    # the port number that a simple flow server listen on (refer to start_simple_server.py)
    addresses = [tuple([remote_ips[idx], SERVER_PORT]) for idx in xrange(0, len(remote_ips), 1)]

    # register signal term
    signal.signal(signal.SIGTERM, signal_term_handler)



    # below code creates and initializes a Flow_Mediator for
    # generating workflows

    local_ip = None

    for ip_val in  host_infcs.values():
        local_ip = ip_val
        break

    try:
        factory = Poisson_Generator_Factory()
        factory.create_generator()
    except Exception as exp:
        print exp
        return

    wait_flow_type = RL_Wait_Flow()  # determines a C array's type
    con = Traffic_Controller(h_interfaces=host_infcs,
            ip_address=(local_ip,
            Flow_Controller.CONTROLLER_PORT_NUM))
    mediator = None

    # might raise an exception
    try:
        mediator = Flow_Mediator(rl_server=rl_server_addr,
                      ip_addresses=addresses,
                      controller=con,
                      wf_type=wait_flow_type,
                      host_index=host,
                      gen_factory=factory,
                      cdf_file=dist_file)

    except:
        print "Flow Mediator could not be instantiated"
        return


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
    if len(sys.argv) < 6:
        print "Please pass more arguments.",
        print "There must a file that stores",
        print "CDF of some distribution,",
        print "a host index within mininet",
        print "all host interfaces within mininet"
        print "and at least two public ip addresses:"
        print "--- Reinforcement learnig server address;"
        print "--- Remote server address(es)."
        print "e.g. start_traffinc_eng.py cdf_file.txt h1",
        print "eth0::10.0.0.1//eth1::10.0.0.2//",
        print "143.125.15.13  143.125.15.16  ..."

    else:


        # preprocess interfaces
        interfaces = _convert_into_dict(sys.argv[3])

        # start running a flow generator
        main(sys.argv[1], sys.argv[2], interfaces, sys.argv[4], sys.argv[5::1])

