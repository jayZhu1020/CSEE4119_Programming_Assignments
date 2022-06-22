import ssl
import sys
from client import Client
from server import Server

errstr = "For registering sever process: \n$ python3 chatapp.py -s <port>\n\n"
errstr += "For registering client process: \n$ python3 chatapp.py -c <name> <server-ip> <server-port> <client-port>\n"

'''
Input: Command Line user input
Output: A server or client object. Will raise an ValueError if invalid user input is given
'''
def parse_command_line_input():
    command_line_input = sys.argv
    client_or_server = None
    # check length of the command line argument
    if len(command_line_input) == 1:
        raise ValueError("Please supply mode and command line arguments\n")
    # check if the mode string is correct
    if not (command_line_input[1] == "-s" or command_line_input[1] == "-c"):
        raise ValueError("Please use -s or -c for mode argument\n")
    # check if the server mode has correct input
    if command_line_input[1] == "-s":
        if len(command_line_input) > 3:
            raise ValueError("Too many arguments\n")
        if len(command_line_input) < 3:
            raise ValueError("Too few arguments\n")
        if not 1024 <= int(command_line_input[2]) <= 65535:
            raise ValueError("Server Port Number not valid, please use port number between 1024 and 65535\n")
        client_or_server = Server(command_line_input[2])
    # check if the client mode has correct input
    if command_line_input[1] == "-c":
        if len(command_line_input) > 6:
            raise ValueError("Too many arguments\n")
        if len(command_line_input) < 6:
            print(len(command_line_input))
            raise ValueError("Too few arguments\n")

        if not 1024 <= int(command_line_input[4]) <= 65535:
            raise ValueError("Server Port Number not valid, please use port number between 1024 and 65535\n")
        if not 1024 <= int(command_line_input[5]) <= 65535:
            raise ValueError("Client Port Number not valid, please use port number between 1024 and 65535\n")
        ip = command_line_input[3].split(".")
        if len(ip) != 4:
            raise ValueError("IP address not valid\n")
        for i in range(4):
            digit = int(ip[i])
            if not 0 <= digit <= 255:
                raise ValueError("IP address not valid\n")

        client_or_server = Client(command_line_input[2], 
                                  command_line_input[3], 
                                  command_line_input[4],
                                  command_line_input[5])

    return client_or_server



try:
    client_or_server_object = parse_command_line_input()
    client_or_server_object.run()
except ValueError as e:
    print(e)
    print(errstr)

