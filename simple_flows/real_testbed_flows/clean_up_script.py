import subprocess




def clean_up():

    clean_cmd = "pkill -f --signal {0} -u jlingys {1}"

    server_exit = "'python2.7 start_simple_server.py'*"
    flow_exit = "'python2.7 start_flow_generator.py'*"
    #SIGTERM = "SIGTERM"
    SIGKILL = "SIGKILL"


    try:
        # kill all remaining servers
        kill_servers = clean_cmd.format(SIGKILL, server_exit)
        subprocess.check_call(
            args=kill_servers,
            stdin=None, stdout=None,
            stderr=None, shell=True)

    except subprocess.CalledProcessError as exp:
        print exp



    try:
        # kill all remaining flow generators
        kill_flows = clean_cmd.format(SIGKILL, flow_exit)
        subprocess.check_call(
            args=kill_flows,
            stdin=None, stdout=None,
            stderr=None, shell=True)

    except subprocess.CalledProcessError as exp:
        print exp



if __name__ == "__main__":
    clean_up()
