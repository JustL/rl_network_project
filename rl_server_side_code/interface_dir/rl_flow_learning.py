'''
This file only contains the interface used by a reinforcement
learning server to pass and get learn parameters. The interface
should be implemented by concrete reinforcement learning models.
'''


class RL_Flow_Learning(object):

    '''
    Interface for initialing a reinforcemnt learning
    model. Since the Q learning is quite often used,
    which is implemented as a deep neural net, by
    calling this method, the neural net would be
    initialized in a conrete class.
    '''
    def start_model(self):
        pass


    '''
    Stop a reinforcemtn learning model from running.
    By calling this method the user might expect to
    save the model paramters, some statistics and so
    on. The taken steps only dpend on the conrete class.
    '''
    def stop_model(self):
        pass


    '''
    Interface used by a reinforcemnt learning server to
    pass some paramters/data (batches) in order to simulate
    an action and receive a reward and update model parameters.
    '''
    def pass_data_for_learning(self, updates):
        pass


