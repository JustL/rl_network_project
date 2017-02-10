from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
#from mininet.clean import Cleanup


import time
import signal
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
term_sign    = 1


def signal_handler(signal, frame):
    global term_sign
    term_sign = 0


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




def simpleTest():
    # Create a simple topology
    # testing the rl approahc
    topo = SingleSwitchTopo(n=NUM_OF_HOSTS)
    net = Mininet(topo)
    net.start()
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    print "Testing network connectivity"
    net.pingAll()

    print "\nGetting network information about the created hosts:\n"

    for host in net.hosts:
        print "Host '{0}' has".format(host.name),
        print "IP address: '{0}',".format(host.IP()),
        print "MAC address: '{0}'".format(host.MAC())

    print "\n********************************************************************\n"


    server_pids = {}   # store process ids in a dictionary
    # command that are run by each of the hosts
    server_cmd = "nohup python2.7 start_simple_server.py {0} > result_server_{1}.out &"
    #generator_cmd = "nohup python2.7 start_flow_generator.py {0} > generator_result_{1}.out"

    # first start running a simple server
    # on each of the hosts
    for host in net.hosts:
        val = host.cmd(server_cmd.format(host.IP(),
            host.name))
        if val !=  None and val != "":
            val = val.split(" ")
            pid = val[1] # second char should be the pid
            server_pids[host.name] = pid[0:-2:1] # get rid of \r\n



    # give some time for the servers to properly start
    time.sleep(10)



    while term_sign:
        pass

    # stopp all processes first
    for host in net.hosts:
        pid = server_pids.get(host.name, None)
        if pid != None:
            host.cmd("kill -s SIGTERM {0}".format(
                server_pids[host.name]))

    net.stop()


if __name__ == "__main__":

    # register for SIGTERM reception
    signal.signal(signal.SIGTERM, signal_handler)

    # Tell mininet to print useful information
    setLogLevel("info")
    simpleTest()


