This file explains how to execute the reinforcement learning 
script so that a reinforcemnt learning server (hereafter referred 
to as the rl_server) gets started. 

The procedure to start the rl_server is very simple:
   1. find the script "start_rl_server.py" and type in the
      following command into a Linux terminal:
      "nohup python start_rl_server.py [ip_address_of_this_server] &".


In order to terminate the process, please type in the following:
    "kill -n SIGTERM [pid]",
    where pid referes to the process id of the python process 
    that executes the server.

It must be mentioned that only the above command must be used 
in order to terminate the process since by using it, the user
will ensure that all allocated resources will be handled properly.

    


