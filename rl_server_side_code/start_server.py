# custom includes that are used to run a
# reinforcement server
from rl_server_dir.rl_server import RL_Server
from algorithm_dir.deep_policy_grad_rl import Deep_Policy_Grad_RL


SERVER_PORT = 20150

if __name__ == "__main__":
    # create and pass the deep reinforcement
    # learning model
    model = Deep_Policy_Grad_RL()
    model.start_model()
    # reinforcement server
    rl_server = RL_Server(ip_address=('127.0.0.1', SERVER_PORT), model=model)

    try:
        # start running the server
        rl_server.start_server()

    except : # catch any exception
        print '\nInterrup has been caught\n'
        rl_server.stop_server()


