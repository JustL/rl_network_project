import subprocess




def clean_up():

    clean_cmd = "sudo pkill -f --signal {0} -u root {1}"

    topo_exit = "'python2.7 rl_test_topology.py'"
    server_exit = "'python2.7 flow_server_side_code/start_simple_server.py'"
    flow_exit = "'python2.7 flow_server_side_code/start_traffic_eng.py'"
    rl_exit = "'python2.7 rl_server_side_code/start_rl_server.py'"
    SIGTERM = "SIGTERM"
    SIGKILL = "SIGKILL"


    try:

        # kill the main script first
        kill_topo = clean_cmd.format(SIGTERM, topo_exit)
        subprocess.check_call(
                args=kill_topo,
                stdin=None, stdout=None,
                stderr=None, shell=True)

    except subprocess.CalledProcessError as exp:
        print exp


    try:
        # kill them remainin  rl servers
        kill_rl_servers = clean_cmd.format(SIGKILL, rl_exit)
        subprocess.check_call(
                args=kill_rl_servers,
                stdin=None, stdout=None,
                stderr=None, shell=True)

    except subprocess.CalledProcessError as exp:
        print exp


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


    try:
        # clean up the mininet allocated resources
        subprocess.check_call(
                args="sudo mn --clean",
                stdin=None, stdout=None,
                stderr=None, shell=True)

    except subprocess.CalledProcessError as exp:
        print exp


if __name__ == "__main__":
    clean_up()
