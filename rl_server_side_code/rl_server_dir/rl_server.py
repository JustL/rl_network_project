# custom imports
from interface_dir.rl_flow_learning import RL_Flow_Learning

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
def model_run_function(model, task_queue, term_event):
    local_copy = [] # the list keeps local copy of tasks

    while not term_event.is_set():   # process computations until
                                     # the parent process dies
        while not local_copy:
            # run first the model on local copies of previous
            # batches
            model.pass_data_for_learning(local_copy.pop(0))

        # done with local copies
        # copy all waiting batches to the local list
        try:
            while 1:
                # dequeue as many batches as possible
                local_copy.append(task_queue.get(False))

        except Empty:
            # means the task_queue has no more tasks
            if not local_copy:
                # no task has been dequeued, wait for at least one
                local_copy.append(task_queue.get(True))


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

    __MAX_WAIT_TASKS = 4     # max number of batches that a model can handle

    def __init__(self, ip_address, model):
        self._m_server = SimpleXMLRPCServer.SimpleXMLRPCServer(ip_address)           # this server executes updates
        self.m_event = threading.Event() # for notifying the other thread
        self._m_batch_queue = Queue(RL_Server.__MAX_WAIT_TASKS) # model data
        # computation is run on a separate thread
        self._m_comp_thread = threading.Thread(target=model_run_function,
              args=(model, self._m_batch_queue, self._m_event))

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
    This method is called when this server
    is being stopped.
    '''
    def stop_server(self):
        try:
            # stop the computation thread
            self._m_event.set()
            while(self._m_comp_thread.is_alive()):
                pass

        except RuntimeError as exp:
            print 'RL_Server:', exp.strerror



if __name__ == '__main__':
    rl = RL_Flow_Learning()
    pass
