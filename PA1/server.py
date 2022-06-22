from email import message
from util import *
from socket import *
import time
class Server:
    def __init__(self, port):
        self.port = int(port)
        self.server_socket = socket(AF_INET, SOCK_DGRAM)
        self.server_socket.bind(("", self.port))
        self.client_table = {}
        self.message_buffer = {}
        self.prev_time = ""

    # the main loop: receive message, perform corresonding action based on message
    def run(self):
        while True:
            message, client_address = self.server_socket.recvfrom(MAX_BUFFER_SIZE)
            client_ip, client_port = client_address
            self.handle_input_event(message.decode(), client_ip, client_port)
        
    # handle the user input from the command line
    def handle_input_event(self, message, client_ip, client_port):
        message_arr = message.split()
        event = message[0]
        # if a new user asks for registration, this new information is updated to the table,
        # and the new table is broadcast to all users 
        if event == CLIENT_INITIAL_REGISTER_EVENT:
            new_name, register_port = message.split()[1:]
            # if there is a collisoin, notify the client object that there is an error
            if new_name in self.client_table:
                msg = SERVER_NAK_NAME_COLLISION
                self.server_socket.sendto(msg.encode(), (client_ip, client_port))
            # otherwise update the table and broadcast the result to all existing clients
            else:
                self.client_table[new_name] = [client_ip, int(register_port), True]
                self.broadcast([new_name])
                msg = SERVER_ACK_INITIAL_REGISTER + " " + str(self.client_table)
                self.server_socket.sendto(msg.encode(), (client_ip, client_port))

        # if a user asks to deregister, send an ack back and deregister it. Then broadcast to all clients
        elif event == CLIENT_DEREGISTER_EVENT:
            dereg_user = message_arr[1]
            self.client_table[dereg_user][IS_ACTIVE] = False
            msg = SERVER_ACK_DEREG
            self.server_socket.sendto(msg.encode(), (client_ip, client_port))
            self.broadcast()
        elif event == CLIENT_REREGISTER_EVENT:
            reg_user = message_arr[1]
            self.client_table[reg_user][IS_ACTIVE] = True
            msg = SERVER_ACK_REREGISTER + " " + str(self.message_buffer.get(reg_user, []))
            if reg_user in self.message_buffer:
                del self.message_buffer[reg_user]
            self.server_socket.sendto(msg.encode(), (client_ip, client_port))
            self.broadcast([reg_user])

        # if a user asks to save a message
        elif event == CLIENT_SAVE_MESSAGE_EVENT:
            sender_name = message_arr[1]
            recipient_name = message_arr[2]
            msg = message[len(event)+len(sender_name)+len(recipient_name)+3:]
            if self.client_table[recipient_name][IS_ACTIVE]:
                # check if the client is actually active
                recipient_ip = self.client_table[recipient_name][IP]
                recipient_port = self.client_table[recipient_name][PORT]
                received, ack = attempt_receive_ACK(recipient_ip, recipient_port, SERVER_CHECK_ACTIVE_EVENT,5,[CLIENT_ACK_ACTIVE])
                # if no response, the client is not active, then change its status to received and 
                if not received:
                    self.client_table[recipient_name][IS_ACTIVE] = False
                    self.server_socket.sendto(SERVER_ACK_SAVE_MESSAGE.encode(), (client_ip, client_port))
                    self.broadcast()
                    saved_message = "{}: {} {}".format(sender_name, time.asctime(), msg)
                    if recipient_name not in self.message_buffer:
                        self.message_buffer[recipient_name] = [saved_message]
                    else:
                        self.message_buffer[recipient_name].append(saved_message)
                else:
                    self.server_socket.sendto(SERVER_NAK_CLIENT_ACTIVE.encode(), (client_ip, client_port))

            else:
                self.server_socket.sendto(SERVER_ACK_SAVE_MESSAGE.encode(), (client_ip, client_port))
                saved_message = "{}: {} {}".format(sender_name, time.asctime(), msg)
                if recipient_name not in self.message_buffer:
                    self.message_buffer[recipient_name] = [saved_message]
                else:
                    self.message_buffer[recipient_name].append(saved_message)
        
        # if the client asks for group chat
        elif event == CLIENT_GROUPCHAT_EVENT:
            sender, timestamp = message_arr[1], message_arr[2]
            self.server_socket.sendto(SERVER_ACK_GROUP_MESSAGE.encode(), (client_ip, client_port))
            # if the client sends duplicate message, only process the first
            if timestamp != self.prev_time:
                self.prev_time == timestamp
                send_msg = SERVER_GROUP_CHAT_EVENT + " " + sender + " " + message[len(CLIENT_GROUPCHAT_EVENT)+len(sender)+len(timestamp)+3:]
                saved_message = "Channel Message {}: {} {}".format(sender, time.asctime(), send_msg)
                # add all active recipients to the set, and store the message for all offline recipeints 
                not_received = set()
                for name, status in self.client_table.items():
                    if status[IS_ACTIVE]:
                        if name != sender:
                            not_received.add(name)
                    else:
                        if name not in self.message_buffer:
                            self.message_buffer[name] = [saved_message]
                        else:
                            self.message_buffer[name].append(saved_message)
                temp_socket = socket(AF_INET, SOCK_DGRAM)
                # send message to all avtive recipients
                for receiver in not_received:
                    receiver_ip, receiver_port = self.client_table[receiver][IP], self.client_table[receiver][PORT]
                    temp_socket.sendto(send_msg.encode(), (receiver_ip, receiver_port))
                # try to received there ack in 500 msc
                temp_socket.settimeout(0.5)
                try:
                    while True:
                        ack_msg, ack_address = temp_socket.recvfrom(MAX_BUFFER_SIZE)
                        print(ack_msg.decode())
                        curr_receiver = ack_msg.decode().split()[1]
                        not_received.remove(curr_receiver)
                except:
                    pass
                # for any client that did not send back an ACK, set its status to false and save the message
                num_not_received = 0
                for receiver in not_received:
                    received, ack = attempt_receive_ACK(self.client_table[receiver][IP], self.client_table[receiver][PORT], 
                                                        SERVER_CHECK_ACTIVE_EVENT, 5, [CLIENT_ACK_ACTIVE])
                    if not received:
                        num_not_received += 1
                        self.client_table[receiver][IS_ACTIVE] = False
                        if receiver not in self.message_buffer:
                            self.message_buffer[receiver] = [saved_message]
                        else:
                            self.message_buffer[receiver].append(saved_message)
                # if there is any change in status, broadcast the change
                if num_not_received > 0:
                    self.broadcast()
                temp_socket.close()


    '''
    broadcast(self, exce = []):
    Input:
    - exce: array of strings

    Output:
    - None

    Description:
    Broadcast to all clients that are active, except the ones with name in exce array
    '''
    def broadcast(self, exce = []):
        msg = SERVER_BROADCAST_EVENT + " " + str(self.client_table)
        for name, client in self.client_table.items():
            if client[IS_ACTIVE] and name not in exce:
                existing_client_ip, existing_client_port = client[IP], client[PORT]
                self.server_socket.sendto(msg.encode(), (existing_client_ip, existing_client_port))


