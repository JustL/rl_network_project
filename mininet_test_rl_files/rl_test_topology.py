from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel


import signal
import time


'''
This file contains a very simple Topology for running simple
flows.

Topology:


                spine_1
             /          \
            /            \
           /              \
        tor_1            tor_2
       |    |           |  |  |
       h1   h2         h3  h4 h5(rl server)


'''

CONTROLLER_PORT = 13557
NUM_OF_HOSTS = 5
term_signal = 1    # for terminating this process


'''
Function gets notified when the user wants to
terminate this program.
'''
def signal_term_handler(signum, frame):
    global term_signal
    term_signal = 0    # reset the flag


'''
Function reads a string
and finds a pid in the string.
'''
def get_pid(return_string):

    # first split into words/expressions
    words = return_string.split(" ")

    pid = None

    # look for the first integer
    for item in words:
        try:
            pos_pid = int(item, 10)
            # no exception -- found an integer
            pid = pos_pid
            break

        except ValueError:
            pass

    return pid




'''
Function interconnects switches
'''
def link_switches(net, tor_switches, spine_switches):
    # each tor switch is connected
    # to every spine switch

    for spine in spine_switches:
        for tor in tor_switches:
            net.addLink(spine, tor)


'''
Function creates links between
hosts and tor switchces
'''
def link_hosts(net, tor_switches, hosts):

    # equally subdivide hosts
    no_hosts = len(hosts)
    no_tors = len(tor_switches)


    hosts_per_switch = no_hosts / no_tors # integer division


    h_local = 0
    # loop through all hosts and connect
    # each of the hosts to a tor
    for s_idx in xrange(0, no_tors-1, 1):
        lower_bound = h_local*hosts_per_switch
        upper_bound = (h_local + 1)*hosts_per_switch

        for h_idx in xrange(lower_bound, upper_bound, 1):
            # connect a host to a tor
            net.addLink(hosts[h_idx], tor_switches[s_idx])

        h_local += 1       # shift by one multiple
                           # of hosts_per_switch


    # last tor has the rest of hosts connected to it
    lower_bound = h_local*hosts_per_switch
    for h_idx in xrange(lower_bound, no_hosts, 1):
        net.addLink(hosts[h_idx], tor_switches[-1])





def simpleTest():

    # first register this program for
    # handling the SIGTERM flag
    signal.signal(signal.SIGTERM, signal_term_handler)


    # Create a simple topology
    # testing the rl approach
    net = Mininet()

    # containers for hosts, tor swithces and spine switches
    hosts = []
    tors = []
    spines = []

    # add hosts first
    for idx in xrange(1, NUM_OF_HOSTS+1, 1):
        hosts.append(net.addHost("h{0}".format(idx)))



    # add switches
    tors.append(net.addSwitch("tor_1"))
    tors.append(net.addSwitch("tor_2"))

    spines.append(net.addSwitch("spine_1"))

    # add a controller
    net.addController(name="c0", port=CONTROLLER_PORT)


    # interconnect switches first
    link_switches(net, tors, spines)

    # interconnect switches and links
    link_hosts(net, tors, hosts)


    net.start()


    print "\nDumping host connections"
    dumpNodeConnections(net.hosts)

    print "\nDumping switch connections"
    dumpNodeConnections(net.switches)

    print "\nTesting network connectivity"
    net.pingAll()

    print "\nGetting network information about the created hosts:\n"

    for host in net.hosts:
        print "Host '%s' has IP address: '%s'," % (host.name, host.IP()),
        print "and MAC address: '%s'" % (host.MAC(), )

    print "\n********************************************************************\n"


    # references to the processes
    server_pids = {}       # pids of servers
    generator_pids = {}    # pids of flow generators
    rl_server_pids = {}    # pids of rl servers


    # create server commands and flow generator
    # commands that will be executed by each of
    # the cluster server
    server_cmd = "nohup python2.7 flow_server_side_code/start_simple_server.py {0} > result_server_{1}.out &"


    generator_cmd_beg = "nohup sudo python2.7 flow_server_side_code/start_traffic_eng.py {0} {1} {2} {3} {4} "
    generator_cmd_end = " > generator_result_{0}.out &"


    rl_server_cmd  = "nohup python2.7 rl_server_side_code/start_rl_server.py {0} > centralised_rl_server_{1}.out &"



    NO_FLOW_SERVERS = len(net.hosts) - 1 # last server is only rl server


    # the reinforcement server must be
    # started first
    rl_host = net.get("h{0}".format(NUM_OF_HOSTS))


    rl_return = rl_host.cmd(rl_server_cmd.format(rl_host.IP(), rl_host.name))

    # some text was returned
    if rl_return != None and rl_return != "":
        pid = get_pid(rl_return)

        if pid != None:
            # pid has beeen successfully
            # retrieved
            rl_server_pids[rl_host.name] = pid


    # loop through all created hosts and
    # start running the server application on them

    for h_idx in xrange(1, NO_FLOW_SERVERS + 1, 1):
        # execute the command
        host = net.get("h{0}".format(h_idx))
        srv_code = host.cmd(server_cmd.format(host.IP(), host.name))

        # store pid
        if srv_code != None and srv_code != "":
            pid = get_pid(srv_code)

            if pid != None:
                # a pid was found
                server_pids[host.name] = pid


    # servers are running
    time.sleep(10) # give some time to successfully
                   # initialize the servers



    # initialize the flow generators
    for h_idx in xrange(1, NO_FLOW_SERVERS + 1, 1):

        host = net.get("h{0}".format(h_idx))
        remote_ips = [] # other servers

        for r_idx in xrange(1, NO_FLOW_SERVERS + 1, 1):
            # add all hosts except for this host
            if h_idx == r_idx:
                continue

            remote = net.get("h{0}".format(r_idx))
            remote_ips.append(remote.IP())
            remote_ips.append(" ") # separator


        # retrieve this hosts interfaces and encode them
        host_interfaces = []

        for if_name, if_obj in host.nameToIntf.items():
            # encode interfaces in the following
            # pattern:
            # "[interface name]:[interface ip]//"
            host_interfaces.append(
                    "{0}:{1}//".format(if_name, if_obj.IP()))

        # start the flow generator appplication on 'host'
        exec_cmd = generator_cmd_beg.format(host.name,
                "".join(host_interfaces), host.IP(),
                rl_host.IP(),
                "".join(remote_ips)) + generator_cmd_end.format(host.name)

        flow_id = host.cmd(exec_cmd)

        if flow_id != None and flow_id != "":
            pid = get_pid(flow_id)

            if pid != None:
                # found pid
                generator_pids[host.name] = pid


    # done starting flows
    print "All flows have been initialized"



    # run until the user wants to terminate
    while term_signal:
        pass


    # stop all applications starting
    # with the rl server(s)

    for key, rl_pid in rl_server_pids.items():

        rl_host = net.get(key)
        if rl_host != None:
            rl_host.cmd("sudo kill -s SIGTERM {0} &".format(rl_pid))


    # Once the rl servers have been
    # stopped, terminate simple servers.
    for host in net.hosts:

        pid = server_pids.get(host.name, None)
        if pid != None:
            # stop the server that runs on
            # the host
            host.cmd("sudo kill -s SIGTERM {0} &".format(pid))
            del server_pids[host.name] # delete the pid


    # servers have been closed
    # start stopping the generators
    for host in net.hosts:

        pid = generator_pids.get(host.name, None)
        if pid != None:
            # stop the flow generator that runs
            #  on the host
            host.cmd("sudo kill -s SIGTERM {0} &".format(pid))
            del generator_pids[host.name] # delete the element



    # all processes have been stopped
    # and killed

    #net.stop()


if __name__ == "__main__":
    # Tell mininet to print useful information
    setLogLevel("info")
    simpleTest()


