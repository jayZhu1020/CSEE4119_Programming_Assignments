from socket import *

'''
----------------
helper functions
----------------
'''

'''
attempt_receive_ACK(self, recipient_ip, recipient_port, msg, trying_time ,expectedACKS)
Input: 
- recipient_ip: string
- recipient_port: int
- msg: string
- trying_time: int
- expectedACKS: array of strings
- timeout: the timeout set for a single try

Output:
- bool: whether an ACK in the array is received
- string: which ACK message it receives

Description:
This function tries to send msg trying_time times to (recipient_ip, recipient_port) 
with timeout 0.5sec.

If an ACK message that starts with expectedACKS is reveived during this process, 
the function returns True and the revceived ack format

Else it returns False and None
'''

def attempt_receive_ACK(recipient_ip, recipient_port, msg, trying_time ,expectedACKS, timeout=0.5):
    temp_socket = socket(AF_INET, SOCK_DGRAM)
    temp_socket.settimeout(timeout)
    received = False
    ack = None
    for _ in range(trying_time):
        try:
            temp_socket.sendto(msg.encode(), (recipient_ip, recipient_port))
            raw_message, server_address = temp_socket.recvfrom(MAX_BUFFER_SIZE)
            if raw_message.decode().split()[0] in expectedACKS:
                ack = raw_message.decode()
                received = True
                break
            else:
                raise TimeoutError()
        except:
            continue
    temp_socket.close()
    return received, ack


'''
---------
Constants
---------
'''
MAX_BUFFER_SIZE = 1024
CLIENT_INITIAL_REGISTER_EVENT = "0"
CLIENT_INDIVCHAT_EVENT = "1"
CLIENT_DEREGISTER_EVENT = "2"
CLIENT_GROUPCHAT_EVENT = "3"
CLIENT_SAVE_MESSAGE_EVENT = "4"
CLIENT_REREGISTER_EVENT = "5"
SERVER_BROADCAST_EVENT = "6"
SERVER_CHECK_ACTIVE_EVENT = "7"
SERVER_GROUP_CHAT_EVENT = "8"
SERVER_ACK_REREGISTER = "ACK_REREG"
SERVER_ACK_INITIAL_REGISTER = "ACK_INITREG"
CLIENT_ACK_ACTIVE = "ACK_ACTIVE"
CLIENT_ACK_INDIV_CHAT = "ACK_CHAT"
SERVER_ACK_DEREG = "ACK_DEREG"
SERVER_ACK_SAVE_MESSAGE = "ACK_SAVE"
SERVER_NAK_CLIENT_ACTIVE = "NAK_SAVE"
SERVER_NAK_NAME_COLLISION = "NAK_COLLISION"
SERVER_ACK_GROUP_MESSAGE = "ACK_GROUP"
IP = 0
PORT = 1
IS_ACTIVE = 2