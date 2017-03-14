from  interface_dir.rl_flow_algorithm import RL_Flow_Algorithm

from keras.models import Sequential, model_from_json
from keras.layers import Dense, Activation
import keras.backend as Backend


import numpy

import json
import xmlrpclib


# these constants are used for updating the learning algorithm
SYSTEM_POSITIVE_REWARD = 1L
SYSTEM_NEGATIVE_REWARD = -1L

class RL_Reward_Struct(object):
    '''
    Can be considered as a C struct
    that stores a tuple of values -
    previous reward, total reward,
    counter.
    '''

    def __init__(self, pred=None):
        self.m_prev_avg_fct = 1.0  # average fct
        self.m_total_reward = 0L   # signed int since reward
                                   # is either -1 or +1
        self.m_count = 0L
        self.m_prev_pred = pred   # stores previous prediction
                                  # It is needed to store this since
                                  # the reward is received in the next
                                  # update

    '''
    Once a new sample is received, update
    this strucutre so that future rewards
    and baselines could be computed.

    Args:
        reward : either -1 or +1 that indicates if the system has done better or worse
                 as compared with previous updates.
    '''
    def update_reward(self, reward, av_fct):
        # if an overflow is possible,
        # try to avoid it
        if self.m_count > 0L and (self.m_count + 1L) < 0L:
            # means an overflow occurs

            # for now don't do anything fancy since since an overflow
            # implies that there have already been many updates to
            # this structure and convergence (nearly optimal solution)
            # is likely achieved.
            self.m_count  = 0L
            self.m_total_reward = 0L

        self.m_total_reward += reward   # total reward is
                                        # updated for baseline

        self.m_prev_avg_fct = av_fct    # previous avg fct is reset
        self.m_count       += 1L        # one more reward received

    '''
    Previous reward is needed for checking if
    the system (flows) have done better as compared
    with the previous update.

    return:
        the rate of previous system update (total_flow_size) / (total_flow_completion_time)
    '''
    def get_prev_avg_fct(self):
        return self.m_prev_avg_fct

    '''
    Returns previous predicitons
    '''
    def get_prev_pred(self):
        return self.m_prev_pred


    '''
    Setter method for previous predictions
    '''
    def set_prev_pred(self, pred):
        self.m_prev_pred = pred

    '''
    An importan method since returns for Monte-Carlo methods
    an unbiased estimate. The baseline is important to reduce
    the variance of a Policy Gradient method.

    return:
        baseline -- mean of all previous rewards
    '''
    def get_baseline(self):
        if self.m_count == 0L:
            return 0.0

        return (self.m_total_reward * 1.0) / self.m_count



class Deep_Policy_Grad_RL(RL_Flow_Algorithm):

    # Actions {priority (int), rate (kbits per second)}:
    # fisrt use this one since these ACTIONS are closer to Linux
    __ACTION_SPACE = [{"priority" : 0, "rate" : 200},
                 {"priority" : 0, "rate" : 400},
                 {"priority" : 2, "rate" : 100},
                 {"priority" : 2, "rate" : 200},
                 {"priority" : 4, "rate" : 100},
                 {"priority" : 4, "rate" : 200},
                 {"priority" : 6, "rate" : 55},
                 {"priority" : 6, "rate" : 105}]


    # Hyperparameters

    __RUN_FLOW_SIZE  = 6           # that many members by the wait cls

    __COMPL_FLOW_SIZE = 7          # completed flow represented by #

    __NO_OF_HIDDEN_UNITS = 5       # number that determines how many
                                   # hidden units are there

    __NO_OF_ACTIONS      = 8       # num of classes =  num of
                                   # priorities * (num of rates)

    __NO_OF_FEATURES     = 130     # number of features a sample has
                                   # (taken from both )
                                   # types of flow - finished and
                                   # running/waiting)
    '''
    Class describes the particular deep learning
    method used for traffic engineering. The chosen
    algorith is based on previous experience and also
    is chosen for simplicity and popularity.
    A Polic Gradient method is chosen and at first
    only one hidden layer is considered
    '''

    def __init__(self):
        RL_Flow_Algorithm.__init__(self)
        # create a map that stores Ip addresesses of servers
        self._m_servers = {}       # dictionary that stores RL_Reward_Structs for each server
        self._m_model  = None      # the deep neural network
        self._m_struct = None      # a struct that stores
                                   # learning statistics about
                                   # a server

        self._m_reward = 0L        # current reward
                                   # (either SYSTEM_POSITVE_REWARD or
                                   # SYSTEM_NEFATIVE_REWARD)

        self._m_baseline = 0.0     # average of of all
                                   # rewards of the latest server

        self._m_epsilon = 0.5      # for the epsilon-greedy approach
        self._m_time    = 1        # for updating epsilon


    '''
    This method must be called before the model
    is used since the method initialises the backend
    neural network.

    Args :
         init_file : a file that stores a pre-trained model
    '''
    def start_model(self, model_file=None, weight_file=None):
        if model_file is None:
            # initialize the model from scratch -- using some techniques
            self._init_from_scratch()

        else:
            # load a pre-trained model from a file
            self._init_from_file(model_file, weight_file)


    '''
    Method initializes the model by using some
    common techiniques to initialize model from
    the same ML family.
    '''
    def _init_from_scratch(self):
        # real neural network that represents the policy
        self._m_model = Sequential([
                        Dense(Deep_Policy_Grad_RL.__NO_OF_HIDDEN_UNITS,
                        input_dim=Deep_Policy_Grad_RL.__NO_OF_FEATURES),
                        Activation('relu'),
                        Dense(Deep_Policy_Grad_RL.__NO_OF_HIDDEN_UNITS),
                        Activation('relu'),
                        Dense(Deep_Policy_Grad_RL.__NO_OF_ACTIONS),
                        Activation('softmax')
                        ])


        # configure the model:
        #      set omptimizer;
        #      set loss function;
        #      set metrics.
        self._m_model.compile(optimizer='sgd',
                             loss=self.loss_function,
                             metrics=['accuracy'])



    '''
    Method loads a pre-trained model from a file and
    uses it for handling actions and providing states
    and rewards.

    Args:
        file : a file that stores a pre-trained model
    '''
    def _init_from_file(self, model_file, weight_file):

        self._m_model = model_from_json(self._load_from_json(model_file))

        if weight_file is not None and isinstance(weight_file, str):
        # if the weights have been saved too,
        # load them
            self._m_model.load_weights(weight_file, by_name=False)

        # a loaded model has to be compiled
        self.compile(optimizer='sgd',
                loss=self.loss_function,
                metrics = ['accuracy'])


    '''
    Method reads a json string from a file
    and returns it

    Args:
        model_filename : JSON file that stores the model to be loaded
    '''
    def _load_from_json(self, model_filename):

        if not isinstance(model_filename, str) or model_filename[-5 : ] != '.json':
            raise RuntimeError("Cannot load from a non-JSON file")

        json_string = None # initiailize the string to nothing
        with open(model_filename, 'r') as json_file:
            json_string = json.load(json_file, encoding='utf-8')

        return json_string


    '''
    The loss function used by the model
    to update neural net parameters.

    It was found that a good loss function is:

    func = - log(pi(s_t, a_t))* [v_t - baseline]  -- minimize this
    objective func <=> maximize expected reward
    '''
    def loss_function(self, y_true, y_pred):

        return -Backend.log(y_pred)*(self._m_reward -
                self._m_baseline)





    '''
    Methods handles all the background complexities
    and saves the model if a file is provided.

    Args:
        model_file : a file that will store the model
        weight_file : a file that stores the weights
    '''
    def stop_model(self, model_file=None, weight_file=None):
        if model_file is not None:
            # save the trained model to the provided file(s)
            self._save_model(model_file, weight_file)

        # finish the model by cleaning up allocated structures
        self._handle_model()



    '''
    Method handles some basic background complexities of the model
    '''
    def _handle_model(self):
        # clean the data structures
        self._m_servers = {}
        self._m_model = None



    '''
    Method saves the model and handles some basic
    background complexities.

    Args:
        model_file : file that stores the model (.json)
        weight_file : file that saves weights
    '''
    def _save_model(self, model_file, weight_file):

        # first check if a JSON file has been passed as
        # only JSOn format is supported
        if not isinstance(model_file, str)  or model_file[-5 : 0] != '.json':
            raise RuntimeError("Cannot save to a non_JSON file and strings must be provided as file paths")

        if weight_file is not None and isinstance(weight_file, str): # if a file passed to save weights, them them
            self._m_model.save_weights(weight_file)

        json_model = self._m_model.to_json()   # save as a json string

        with open(model_file, 'w') as json_file:
            json.dump(json_model, json_file, encoding='utf-8')


    '''
    Core method of the class since it uses the model
    to run the state transition so that the weights of
    the backend neural net would be updated.

    Args:
        updates : custom set that stores the ip_address of
        a remote server and observations in terms of waiting/
        running flows and completed flows
    '''
    def pass_data_for_learning(self, updates):
        ip_address, wait_flows, completed_flows = updates


        ip_address = tuple(ip_address) # need to convert into a tuple

        if ip_address not in self._m_servers:
            # a new server sends a request, allocate a new
            #flow info struct for it
            self._m_servers[ip_address] = RL_Reward_Struct(
                numpy.zeros((1,Deep_Policy_Grad_RL.__NO_OF_ACTIONS),
                dtype=numpy.float32))

        # first the received reward has to be computed
        self._m_struct = self._m_servers[ip_address]
        self._compute_reward(completed_flows)



        # since for this case only the number dedined by
        # __NO_OF_FEATURES determines how many flows are
        # considered per flow, need to pad or cut some flows
        features =  self._preprocess_flows(wait_flows,
                                      completed_flows)


        # use the neural net for making a decision
        self._make_decision(features, ip_address)


    '''
    Method takes all flows passed by a server and preprocess
    them so that a fixed number of flows only is considered.
    So padding or cut of might be applied.

    Args:
        wait_flows : waiting/running flows on a server
        completed_flows : completed flows on a server


    return:
        features that can be passed to a neural net
    '''
    def _preprocess_flows(self, wait_flows, completed_flows):
        # considered to take the same number of wait and
        # completed flows first.
        # How the below steps are implemented should be clear
        # after reading the flow_impl.py module from
        # flow_server_side_code.
        # Now taking 10 and 10 flows
        if len(wait_flows) < 10:
            # needs some padding
            need_to_add = 10 - len(wait_flows)
            for _ in xrange(need_to_add):
                # add a tuple that represents
                # a waiting/running flow
                wait_flows.append(
                        Deep_Policy_Grad_RL.__RUN_FLOW_SIZE * [0])

        # do the same thing with completed flows
        if len(completed_flows) < 10:
            need_to_add = 10 - len(completed_flows)
            for _ in xrange(need_to_add):
                # keep adding the tuple that
                # represemts a completed flow
                completed_flows.append(
                        Deep_Policy_Grad_RL.__COMPL_FLOW_SIZE * [0])

        wait = numpy.array(wait_flows[-10::1]).reshape((1, 10*len(wait_flows[-1])))

        completed = numpy.array(completed_flows[-10::1]).reshape((1, 10*len(completed_flows[-1])))


        return numpy.concatenate((wait, completed), axis=1)



    '''
    The method takes all completed flows and updates
    the objects (model's) internal states such as
    rewards, baselines.

    Args :
        flows : completed flows on a remote server
    '''
    def _compute_reward(self, flows):
        if not flows:

            # nothing to observe
            self._m_reward = 0L
            self._m_baseline = 0.0

            return

        # reward is computed by comparing previous
        # average completion time and current one
        all_fcts =  0.0


        # a list of list-flows
        for item in flows:
            all_fcts += item[-1] # fct is the last item

        # compute a new reward
        avg_fct = (all_fcts / len(flows))

        self._m_reward = SYSTEM_NEGATIVE_REWARD if (
                avg_fct / self._m_struct.get_prev_avg_fct()
                ) > 1.0 else SYSTEM_POSITIVE_REWARD

        self._m_struct.update_reward(self._m_reward, avg_fct)
        self._m_baseline = self._m_struct.get_baseline()


    '''
    Methods takes a state represented by completed and waiting/running
    flows and computes probabilities for each of the actions.
    The epsilon-greedy approach is taken since it's simple and
    effective.

    Args :
        features : a numpy array that can be fed into a neural net
        server_address : the IP of the server that needs to be updated
    '''
    def _make_decision(self, features, server_address):
       predictions =  self._m_model.predict(x=features, batch_size=1, verbose=0)

       act_index = 0
       if self._m_time > 0:
           # since epsilon-greedy is used, throw a die
           # in order to choose the next action

           if predictions[0].max() < (self._m_epsilon / self._m_time):
               act_index = numpy.random.randint(low=0,
                       high=Deep_Policy_Grad_RL.__NO_OF_ACTIONS,
                       size=None, dtype=numpy.int)

           else: # be greedy and choose the predicted value
               act_index = predictions[0].argmax()

           # update epsilon value
           self._m_time = self._m_time + 1 if (
                   self._m_time + 1) > 0 else 0
           self._m_epsilon = (self._m_epsilon / self._m_time) if self._m_time != 0 else 0.0

       else: # epsilon-greedy has converged
            act_index = predictions[0].argmax() # always act greedy


       # send the received value to the remote server

       # the below should never happen, but safety
       act_index = act_index % Deep_Policy_Grad_RL.__NO_OF_ACTIONS
       client = None
       try:
           client = xmlrpclib.ServerProxy(
                   "http://" + server_address[0] + ":"
                   + str(server_address[1]))
           # send an update
           client.update_flow_parameters(Deep_Policy_Grad_RL.__ACTION_SPACE[act_index])
       except:
           # an exception might be thrown if the remote client
           # has closed its listening process
           pass

       # train on the same data too and use previous
       # labels
       self._m_model.fit(features, self._m_struct.get_prev_pred(),
               batch_size=1, nb_epoch=1, verbose=0)

       # update prev predictions

       prob = predictions[0][act_index]
       predictions = numpy.zeros((1, Deep_Policy_Grad_RL.__NO_OF_ACTIONS),
               dtype=numpy.float32)
       predictions[0][act_index] = prob
       self._m_struct.set_prev_pred(predictions)

       # update infor related to a particular server
       del self._m_servers[server_address]
       self._m_servers[server_address] = self._m_struct
       self._m_struct = None


    '''
    Public method used by a remote server to remove itself
    from this model's server list. In other words, a remote
    server calls this method when it wants to stop sending
    its updates to the model.

    Args:
        ip_address : ip address of a remote server

    Return:
        returns the state of a successful deletion
    '''
    def unregister_from_learning(self, ip_address):

        address = tuple(ip_address) # need to convert into a tuple
                                    # since RPC converts into a list

        if address in self._m_servers:
            # if the passed ip has been registered within
            # this model, delete it -- unregister it.
            del self._m_servers[address]

