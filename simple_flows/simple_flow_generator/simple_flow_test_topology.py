from mininet.topo import Topo
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
       |    |           |    |
       h1   h2         h3    h4


'''

NUM_OF_HOSTS = 4
term_signal = 1    # for terminating this process


'''
Function gets notified when the user wants to
terminate this program.
'''
def signal_term_handler(signum, frame):
    global term_signal
    term_signal = 0    # reset the flag




class SingleSwitchTopo(Topo):
    "Single switch connected to n hosts"

    def build(self, n=5):

        # creates the switches interconnected as
        # depicted above.
        spine_1 = self.addSwitch("spine_1")
        tor_1 = self.addSwitch("tor_1")
        tor_2 = self.addSwitch("tor_2")
        self.addLink(tor_1, spine_1)
        self.addLink(tor_2, spine_1)


        # determine the numbers of hosts
        # for each of the clusters
        cluster_1 = NUM_OF_HOSTS / 2

        for h_idx in xrange(1, cluster_1+1, 1):
            host = self.addHost("h{0}".format(h_idx))
            self.addLink(host, tor_1)

        for h_idx in xrange(cluster_1+1, NUM_OF_HOSTS+1, 1):
            host = self.addHost("h{0}".format(h_idx))
            self.addLink(host, tor_2)



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




def simpleTest():

    # first register this program for
    # handling the SIGTERM flag
    signal.signal(signal.SIGTERM, signal_term_handler)


    # Create a simple topology
    # testing the rl approach
    topo = SingleSwitchTopo(n=NUM_OF_HOSTS)
    net = Mininet(topo)
    net.start()
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    print "Testing network connectivity"
    net.pingAll()

    print "\nGetting network information about the created hosts:\n"

    for host in net.hosts:
        print "Host '%s' has IP address: '%s'," % (host.name, host.IP()),
        print "and MAC address: '%s'" % (host.MAC(), )

    print "\n********************************************************************\n"


    # references to the processes
    server_pids = {}       # pids of servers
    generator_pids = {}    # pids of flow generators


    # create server commands and flow generator
    # commands that will be executed by each of
    # the cluster server
    server_cmd = "nohup python2.7 start_simple_server.py {0} > result_server_{1}.out &"

    generator_cmd_beg = "nohup python2.7 start_flow_generator.py {0} "
    generator_cmd_end = " > generator_result_{0}.out &"


    # loop through all created hosts and
    # start running the server application on them

    for host in net.hosts:
        # execute the command
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
    for host in net.hosts:
        remote_ips = [] # other servers

        for remote in net.hosts:
            # add all hosts except for this host
            if host.name == remote.name:
                continue

            remote_ips.append(remote.IP())
            remote_ips.append(" ") # separator


        # start the flow generator appplication on 'host'
        exec_cmd = generator_cmd_beg.format(host.name) + "".join(remote_ips)  + generator_cmd_end.format(host.name)

        flow_id = host.cmd(exec_cmd)

        if flow_id != None and flow_id != "":
            pid = get_pid(flow_id)

            if pid != None:
                # found pid
                generator_pids[host.name] = pid


    # done starting flows

    # run until the user wants to terminate
    while term_signal:
        pass


    # stop all applications starting
    # with the servers

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

    net.stop()


if __name__ == "__main__":
    # Tell mininet to print useful information
    setLogLevel("info")
    simpleTest()


