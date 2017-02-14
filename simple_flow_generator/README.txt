This file explains how to generate flows among a cluster's 
servers.



First of all, each of the server has to execute the 
"start_simple_server.py" script in order to start a server
that sends responses to programs that generate flows. If
the order is not followed, unexpected outcomes might occur.

So execute on each of the cluster server the following:
    "nohup python start_simple_server.py [ip_of_the_server]"

An ip of the cluster server has to be passed so that the server
could bind the application to an ip interface. PORT number must not
be passed since all servers listen on the same port number.


In order to terminate the process type in the following command:
    "kill -n SIGTERM [pid]",
    where pid referes to the server's process id.


Once a server has been started on each of the cluster's servers,
traffic engineering can be started by executing the following 
command on each of the servers:
    "nohup python start_traffic_eng.py [this_ip_interface] 
    [rl_server_ip] [array_of_remote_ips]"

    this_ip_interface   - an ip address of this server
    rl_server_ip        - the ip of a rl server (no PORT NUM)
    array_of_remote_ips - ips (no port) of servers that this server
                          will communicate with


The traffic engineering must be temrinated by executing the command:
    "kill -n SIGTERM [pid]",

     where pid is the process id of the traffic engineering process.
     The id should be a low python process value since this
     process creates many extra processes. When terminating, make sure
     you know which process to terminate.
   
     


