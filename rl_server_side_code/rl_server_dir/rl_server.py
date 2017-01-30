# std library
import SimpleXMLRPCServer
import threading
from Queue import Queue, Empty


'''
This function is run by the model thread so that the computation
would be separated from request handling.

Args:
    model      : the reinforcement learning  model interface
    task_queue : a queue that stores all available flows
'''
def model_run_function(model, task_queue, term_event, clean_ip_queue):
    local_copy = []                # the list keeps local copy of tasks
    ips_to_remove = []             # list for unregistering from updates

    CHECK_FOR_UNREGISTRATION = 5   # check for cleaning after a number of
                                   # updates
    cur_count = 0                  # how many updates happened


    while not term_event.is_set():   # process computations until
                                     # the parent process dies

        # copy all waiting batches to the local list
        try:
            while 1:
                # dequeue as many batches as possible
                local_copy.append(task_queue.get(False))

        except Empty:
            pass
            # means the task_queue has no more tasks

        # process the tasks that have been added to the local list
        while local_copy:
            # process data that the local list has
            model.pass_data_for_learning(local_copy.pop(0))

        cur_count += 1  # update the cleaning counter

        # after processing data, check if any servers
        # want to be unregistered
        if cur_count == CHECK_FOR_UNREGISTRATION:

            try:
                while 1:
                   ips_to_remove.append(clean_ip_queue.get(False))

            except Empty:
                pass

            # unregister some remote servers
            while ips_to_remove:
                model.unregister_from_learning(ips_to_remove)

            # reset the counter
            cur_count = 0




    # handled all task cases. The below code stops the model
    # since it can olny be run if the parent process is
    # being stopped.
    model.stop_model()

    # done running computations



class RL_Server(object):
    '''
    Class implements a simple reinforcemtn learning server.
    All the servers within the cluster of servers that is managed
    by a centralized rl server, must communicate with this server
    in order to get updated traffic control parameters.

    Current Parameters : (priority, rate)

    Input parameters   : completed flows (FCT, size, priority),
                         waiting/running flows (size, priority)
    '''
    __RL_SERVER_PORT_NUM = 32202 # global constant that should be used
                               # to run an rl server
    __MAX_WAIT_TASKS = 4     # max number of batches that a model can handle

    def __init__(self, ip_address, model):
        self._m_server = SimpleXMLRPCServer.SimpleXMLRPCServer((ip_address, RL_Server.__RL_SERVER_PORT_NUM))
        # this server executes updates
        self._m_event = threading.Event() # for notifying the other thread
        self._m_batch_queue = Queue(RL_Server.__MAX_WAIT_TASKS) # model data
        self._m_clean_ips = Queue(RL_Server.__MAX_WAIT_TASKS) # a queue of ip addresses that have to be removed from the model's algorithm
        # computation is run on a separate thread
        self._m_comp_thread = threading.Thread(target=model_run_function,
              args=(model, self._m_batch_queue, self._m_event, self._m_clean_ips))
        self._m_comp_thread.start() # start running the thread

    '''
    An interface that the RPC server owned by this class
    uses to comminicate with its proxies.

    Args :
         ip_address : the ip address of the RPC server that runs on the
                      requester (a cluster server)
         wait_flows : a list of waiting flows
         done_flows : a list of finished flows

    '''
    def pass_flow_info(self, train_batch):

        # enqueue the new batch on the processor queue
        self._m_batch_queue(train_batch, True) # use blocking call


    '''
    For testing a connection only.
    The method is only a means of letting a remote client
    to know that the connection has successfully been established.
    '''

    def test_connection(self):
        pass


    '''
    Method is used by a remote server to notify this
    reinforcement learning server that the remote server
    will not send any more updates.

    Args:
        ip_address : ip address of a remote server that stops
                     updating
    '''
    def unregister_server(self, ip_address):
        self._m_clean_ips.put(ip_address, True) # use blocking put



    '''
    Method called to run an infinite loop
    in order to put the server in a waiting
    state.
    '''
    def start_server(self):
        while 1:
            pass



    '''
    This method is called when this server
    is being stopped.
    '''
    def stop_server(self):
        try:
            # stop the computation thread
            self._m_event.set()
            self._m_comp_thread.join()


        except RuntimeError:
            raise


