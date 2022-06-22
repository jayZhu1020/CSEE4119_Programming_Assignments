# Jiang Zhu jz3417 - CSEE 4119 PA1

## General Info:

To compile the program:

General syntax:
```shell
$ python3 ChatApp.py <mode> <command-line arguments>
```

Registering a client:
```shell
$ python3 ChatApp.py -c <name> <server-ip> <server-port> <client-port>
```

Requirements:
1. `<name>` must not collide with any existing client
2. `<server-ip> <server-port>` must correspond to a running server
3. `<client-port>` must be between 1024 and 65535


Registering a server:
```shell
$ python3 ChatApp.py -s <port>
```

Requirements:
1. `<port>` must be between 1024 and 65535

## Commands and functionalities:
After successfully registered, the screen will be prompted `>>> `. Avaliable functionalities include:

1. To send a message to a existing client, use
    
    `>>> send <name> <message>`
    
    if the client is inactive, message will be sent to the server instead. Otherwise, a message 
    
    `>>> <sender-name>: <message>` 
    
    will be appear in the receiver's window.
2. To deregister an online client use
   
   `>>> dereg <username>`
   
   the `<username>` must match the current username.
3. To register back an offline client, use 
   
    `>>> reg <username>`
    
    the `<username>` must match the current username and the user must be offline. After re-registering, the program will display all accumulated offline messages.
4. To send a groupchat to all clients, use 
   
   `>>> send_all <message>`
   
   the message will be displayed to all active clients excluding the sender, the message to offline clients will be saved in server. 


## Assumptions (Not handled by the program if they are false):

## General Assumptions:
1. no packet loss is assumed because otherwise a TCP socket can be used instead. However, packet delay is assumed.
2. Each time the client needs to communicate with other clients or the server, a new socket will be created. The initial registered socket is only used for listening. After the communication, the server will be closed


## Specific Assumption:

### Registration / Deregistration: 
1. For a given (ip, port) pair, there can be one name associate to it. If a new client with the same (ip, port) registers, I assume that the prvious name that associates to such pair will never be registered again
2. When a client is silent leaving, it will not come back with the same name
3. When a client calls dereg, the command line will not quit and still be prompted `>>> `, but only `>>> reg <username>` command will be allowed

### Chatting / Offline Chat:
1. When a save message request is sent to server and the server table says that the recipient is active, it will communicate with the intended recipient to see if it is still active. If it receives acknowlegement, it will inform the sender that the receiver is active. Otherwise, it accepts the save message request and change the recipient's status to offline. 


