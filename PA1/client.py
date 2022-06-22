from curses.ascii import ACK
from multiprocessing.sharedctypes import Value
from pickle import FALSE
from util import *
from socket import *
import threading
import time

client_input_err_str = "Please use the following commands:\n"
client_input_err_str += "For sending individual message:\n $ >>> send <name> <message>\n"
client_input_err_str += "For registering:\n $ >>> reg <nick-name>\n"
client_input_err_str += "For de-registering:\n $ >>> dereg <nick-name>\n"
client_input_err_str += "For sending group message:\n $ >>> send_all <message>"

class Client:

    '''
    __init__(self, name, server_ip, server_port, client_port):
    intialize the client object. Record its nickname, the server IP it is sending
    to, and the table of other clients that will be dynamically updated from the server
    '''
    def __init__(self, name, server_ip, server_port, client_port):
        self.name = name
        self.server_ip = server_ip
        self.server_port = int(server_port)
        self.client_port = int(client_port)
        self.client_socket = socket(AF_INET, SOCK_DGRAM)
        self.client_socket.bind(("", self.client_port))
        self.client_table = {}
        self.initial_register()
        self.is_active = True
        print(">>> Welcome, you are registered.")
    
    '''
    register(self):

    for registering new users when command line python3 chatapp.py -c is called. Will raise
    an value error if the username already exists
    '''
    def initial_register(self):
        msg = CLIENT_INITIAL_REGISTER_EVENT + " " + self.name + " " + str(self.client_port)
        received, ack = attempt_receive_ACK(self.server_ip, self.server_port, msg, 5, [SERVER_NAK_NAME_COLLISION, SERVER_ACK_INITIAL_REGISTER])
        if not received:
            raise ValueError("Server Not Responding, cannot register")
        else:
            if ack.split()[0] == SERVER_NAK_NAME_COLLISION:
                raise ValueError("The name is already registered")
            else:
                table_str = ack[len(SERVER_ACK_INITIAL_REGISTER)+1:]
                self.client_table = eval(table_str)
    '''
    run(self):

    enters the main loop for client listening to both user input and socket input using two
    threads
    '''
    def run(self):
        user_input_thread = threading.Thread(target=self.handle_user_input_event)
        socket_input_thread = threading.Thread(target=self.handle_socket_input_event)
        # set the socket thread to be daemon, so that when the user input exits, the whole 
        # program exits
        socket_input_thread.daemon = True
        user_input_thread.start()
        socket_input_thread.start()


    '''
    handle_user_input_event(self):

    The thread for handling the command line input entered by the user. 
    Will raise an value error if invalid input is given
    '''
    def handle_user_input_event(self):
        while True:
            try:
                command = input(">>> ")
                command_arr = command.split()
                # error checking for empty input
                if len(command_arr) == 0:
                    continue
                event = command_arr[0]
                if not self.is_active and event != "reg":
                    raise ValueError("You are offline. Please use reg to register back")


                # handling send instruction
                if event == "send":
                    # error checking for too few arguments or non-existing client
                    if len(command_arr) <= 2:
                        raise ValueError("Too few arguments")
                    recipent_name = command_arr[1]
                    if recipent_name not in self.client_table:
                        raise ValueError("The recipient does not exist")
                    chat_msg = command[len(event)+len(recipent_name)+2:]
                    send_msg = CLIENT_INDIVCHAT_EVENT + " " + self.name + " " + chat_msg
                    save_msg = CLIENT_SAVE_MESSAGE_EVENT + " " + self.name + " " + recipent_name + " " + chat_msg
                    # handle the case of sending to oneself
                    if recipent_name == self.name:
                        print(">>> Message received by {}\n>>> {}: {}".format(recipent_name, self.name, chat_msg))
                        continue
                    # if the client is active in the local table
                    if self.client_table[recipent_name][IS_ACTIVE]:
                        # send the message to the client and expect and ACK from it
                        recipient_ip, recipient_port = self.client_table[recipent_name][IP], self.client_table[recipent_name][PORT]
                        received, ack = attempt_receive_ACK(recipient_ip, recipient_port, send_msg, 1, ["ACK_CHAT"])
                        # if it is not received, send a save-message request to server
                        if not received:
                            print(">>> No ACK from {}, message sent to server.".format(recipent_name))
                            received_from_server, server_ack = attempt_receive_ACK(self.server_ip, self.server_port
                                                                                        ,save_msg, 1
                                                                                        ,[SERVER_ACK_SAVE_MESSAGE, SERVER_NAK_CLIENT_ACTIVE], timeout=3.0)
                            # if the server is not responding, exit the program
                            if not received_from_server:
                                print(">>> Server not responding\n>>> Exiting")
                                exit()
                            else:
                                # if the server acknowledges the save, change the 
                                # corresponding recipeint status to inactive 
                                if server_ack == SERVER_ACK_SAVE_MESSAGE:
                                    print(">>> Messages received by the server and saved")
                                    self.client_table[recipent_name][IS_ACTIVE] = False
                                else:
                                    print(">>> Client {} exists!!!".format(recipent_name))
                        else:
                            print(">>> Message received by {}".format(recipent_name))

                    # else the table say that the client is not active
                    else:
                        received_from_server, server_ack = attempt_receive_ACK(self.server_ip, self.server_port
                                                                            ,save_msg, 1
                                                                            ,[SERVER_ACK_SAVE_MESSAGE], timeout=3.0)
                        if not received_from_server:
                            print(">>> Server not responding\n>>> Exiting")
                            exit()
                        else:
                            print(">>> Messages received by the server and saved")
                                

                # handling deregistration 
                elif event == "dereg":
                    if len(command_arr) == 1:
                        raise ValueError("Too few arguments")
                    if len(command_arr) > 2:
                        print(command_arr)
                        print(len(command_arr))
                        raise ValueError("Too many arguments")
                    if command_arr[1] != self.name:
                        raise ValueError("Username does not match")
                    dereg_message = CLIENT_DEREGISTER_EVENT + " " + self.name
                    received, ack = attempt_receive_ACK(self.server_ip, self.server_port,
                                                        dereg_message, 5, ["ACK_DEREG"])
                    self.is_active = False
                    if not received:
                        print(">>> Server not responding\n>>> Exiting")
                        exit()
                    else:
                        print(">>> You are Offline. Bye.")

                    


                # handling registration
                elif event == "reg":
                    if len(command_arr) < 2:
                        raise ValueError("Too few arguments")
                    if len(command_arr) > 2:
                        raise ValueError("Too many arguments")
                    if command_arr[1] != self.name:
                        raise ValueError("Username does not match")
                    if self.is_active:
                        raise ValueError("You are already online")
                    self.is_active = True
                    registration_msg = CLIENT_REREGISTER_EVENT + " " + self.name
                    received, ack = attempt_receive_ACK(self.server_ip, self.server_port, registration_msg, 5, [SERVER_ACK_REREGISTER])
                    if not received:
                        print(">>> Server not responding\n>>> Exiting")
                        exit()
                    else:
                        print(">>> Welcome back")
                        unreceived_msg_arr = eval(ack[len(SERVER_ACK_DEREG)+1:])
                        if len(unreceived_msg_arr) > 0:
                            print(">>> You Have Messages")
                            for i in range(len(unreceived_msg_arr)):
                                print(">>> {}".format(unreceived_msg_arr[i]))
                        
                # handling group chat
                elif event == "send_all":
                    # send the groupchat instruction to server, use the time that the message is created 
                    # as an unique identifier
                    group_message = CLIENT_GROUPCHAT_EVENT + " " + self.name + " " + str(time.time())+ " " + command[len(event)+1:]

                    received, ack = attempt_receive_ACK(self.server_ip, self.server_port, 
                                                        group_message, 1, [SERVER_ACK_GROUP_MESSAGE])
                    if not received:
                        received_retry, ack = attempt_receive_ACK(self.server_ip, self.server_port, 
                                                        group_message, 5, [SERVER_ACK_GROUP_MESSAGE])
                        if not received_retry:
                            print(">>> Server not responding")
                        else:
                            print(">>> Message received by Server")
                    else:
                        print(">>> Message received by Server")

                # for all other commands, raise an error
                else:
                    raise ValueError("Invalid command\n")
                

            except ValueError as e:
                print(e)
                print(client_input_err_str)

    '''
    handle_socket_input_event(self):

    The thread for handling the socket input entered by the user. 
    '''
    def handle_socket_input_event(self):
        while True:
            raw_message, sender_address = self.client_socket.recvfrom(MAX_BUFFER_SIZE)
            sender_ip, sender_port = sender_address
            # if the user is not active, disregard any socket input
            if not self.is_active:
                continue
            message = raw_message.decode()
            message_arr = message.split()
            mode = message_arr[0]
            # handle server broadcast table update
            if mode == SERVER_BROADCAST_EVENT:
                self.client_table = eval(message[len(mode)+1:])
                print("client table updated.\n>>> ", end="")
            # handle individual chat sent from other servers
            elif mode == CLIENT_INDIVCHAT_EVENT:
                # send an ACK back to the sender and print the message
                self.client_socket.sendto(CLIENT_ACK_INDIV_CHAT.encode(), (sender_ip, sender_port))
                sender = message_arr[1]
                chat_message = message[len(mode)+len(sender)+2:]
                print("{}: {} \n>>> ".format(sender, chat_message), end = "")
            # handle server asking the status of the current client
            elif mode == SERVER_CHECK_ACTIVE_EVENT:
                # reply that the client is active
                self.client_socket.sendto(CLIENT_ACK_ACTIVE.encode(), (self.server_ip, self.server_port))
            elif mode == SERVER_GROUP_CHAT_EVENT:
                sender = message_arr[1]
                group_msg = message[len(SERVER_GROUP_CHAT_EVENT)+len(sender)+2:]
                print("Channel Message {}: {}\n>>> ".format(sender, group_msg), end = "")
                ack_msg = SERVER_ACK_GROUP_MESSAGE + " " + self.name
                self.client_socket.sendto(ack_msg.encode(), (sender_ip, sender_port))
                



