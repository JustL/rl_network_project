from interface_dir.rl_flow_learning import RL_Flow_Learning


class Deep_Q_RL(RL_Flow_Learning):
    '''
    Class describes the particular deep learning
    method used for traffic engineering. The chosen
    algorith is based on previous experience and also
    is chosen for simplicyt and popularity.
    '''

    def __init__(self):
        super.__init__(self)


    '''
    This method must be called before the model
    is used since the method initialises the backend
    neural network.

    Args :
         init_file : a file that stores a pre-trained model
    '''
    def start_model(self, init_file=None):
        if init_file is None:
            # initialize the model from scratch -- using some techniques
            self._init_from_scratch()

        else:
            # load a pre-trained model from a file
            self._init_from_file(init_file)


    '''
    Method initializes the model by using some
    common techiniques to initialize model from
    the same ML family.
    '''
    def _init_from_scratch(self):
        pass


    '''
    Method loads a pre-trained model from a file and
    uses it for handling actions and providing states
    and rewards.

    Args:
        file : a file that stores a pre-trained model
    '''
    def _ini_from_file(self, init_file):
        pass


    '''
    Methods handles all the background complexities
    and saves the model if a file is provided.

    Args:
        save_file : a file that will store the model
    '''
    def stop_model(self, save_file=None):
        if save_file is None:
            # no need to save the model, do some basic
            # changes
            self._handle_model()
        else:
            # save the trained model to the proved file
            self._save_model(save_file)

    '''
    Method handles some basic background complexities of the model
    '''
    def _handle_model(self):
        pass

    '''
    Method saves the model and handles some basic
    background complexities.

    Args:
        save_file : file that stores the trained model
    '''
    def _save_model(self, save_file):
        # do some work in order to save
        # TODO

        # call basic handling
        self._handle_model()

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
        pass
