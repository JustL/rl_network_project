# custom includes that are used to run a
# reinforcement server
from rl_server_dir.rl_server import RL_Server
from algorithm_dir.deep_policy_grad_rl import Deep_Policy_Grad_RL

import sys
import threading
import Queue

# this is a global flag that is used to terminate this
# process
term_event = 1



# a separate thread is
# running the reinforcement learning server
def run_rl_server(queue):
    server = queue.get()

    try:
        # might throw an exception
        server.start_server()
    except:
        pass

    print "Server Thread is terminating"



# gets called once "SIGTERM" is used
def signal_term_handler(signal, frame):
    global term_event
    term_event = 0


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print "Please enter an ip address for this rl server"
        print "(e.g., '127.0.0.1')"
        sys.exit(0)

    # create and pass the deep reinforcement
    # learning model
    model = Deep_Policy_Grad_RL()
    # reinforcement server
    rl_server = RL_Server(ip_address=sys.argv[1], model=model)

    # create a queue so that the created server could be
    # passed to a new thread
    m_queue = Queue.Queue(1)
    m_queue.put(rl_server)

    # new thread runs the server
    thread = threading.Thread(target=run_rl_server, args=(m_queue,))
    thread.start()  # start the thread

    # wait until the term signal is set
    while term_event:
        pass


    try:
        # start running the server
        rl_server.stop_server()

    except : # catch any exception
        pass

    # wait until the thread terminates
    thread.join()

