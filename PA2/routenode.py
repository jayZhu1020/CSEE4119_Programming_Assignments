import random
from socket import *
import sys
import time
from threading import Timer, Thread
import heapq

INPUTWARNING = """
Please enter the correct input:\n
python3 routenode.py <dv/ls> <r/p> <update-interval> <local-port> <neighbor1-port> <cost-1> ... [last] [<cost-change>]
"""

MAXBUFFERSIZE = 1024

LINKCOSTCHANGEDELAY = 30.0

ROUTING_INTERVAL = 30.0

class Node:

    '''================================================================='''
    '''                                                                 '''
    '''         Main Function, Input Parsing and printing table         '''
    '''                                                                 '''
    '''================================================================='''

    '''
    Function: main()

    Functionality: wraps the entire pipeline
    '''
    def main(self):
        # initialize necessary variables
        self.neighbors = {} # maps a neighbor to the direct cost (adjacent_neighbor : cost)
        self.protocol = None # the protocol on which the current node is operating, "dv" or "ls"
        self.mode = None # mode on which the current node is operating, "r" or "p"
        self.local_port = None # local port read from the command line
        self.IP = "127.0.0.1" # IP, by default the recursive root
        self.update_interval = None # The update interval specified by the input
        # processing input
        try:
            self.is_last, self.update_cost, self.max_port = self.parseInput()
        except:
            print(INPUTWARNING)
            exit(0)
        

        # create socket
        self.node_socket = socket(AF_INET, SOCK_DGRAM)
        self.node_socket.bind((self.IP, self.local_port))
        # depending on the protocal, enter different loops
        if self.protocol == "dv":
            self.protocol_dv()
        elif self.protocol == "ls":
            self.protocol_ls()
        else:
            raise ValueError()

    '''
    Function: parseInput()
    Input: 
        - sys.argv
    Output: 
    throws exception, or global table and information being initialized and also return
        - is_last : whether the current node is the last node
        - update_cost: if the current node is the last node, what the cost changes to
        - max_port: the maximum port number to which the edge cost will be updated

    Functionality: does basic error checking on input, cases that are not handled are specified in README.txt
    '''
    def parseInput(self):
        # Correct Input format:
        #              0          1      2          3                4                5          6         
        # python3 routenode.py <dv/ls> <r/p> <update-interval> <local-port> <neighbor1-port> <cost-1> ... [last] [<cost-change>]
        # at least five arguments needed
        if len(sys.argv) < 5:
            raise ValueError()
        # check if the protocal is either dv or ls
        if sys.argv[1] not in ["dv", "ls"]:
            raise ValueError()
        
        # check if the mode is either regular or posion reverse
        if sys.argv[2] not in ["r", "p"]:
            raise ValueError()
        # check if update_interval is a number

        if not sys.argv[3].isnumeric():
            raise ValueError()
        # check if the port is > 1024
        if not sys.argv[4].isnumeric() or int(sys.argv[4]) < 1024:
            raise ValueError()
        
        self.protocol, self.mode, self.update_interval, self.local_port = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        # start processing
        is_last = False
        update_cost = None
        max_port = 0
        curr_command_idx = 5
        while curr_command_idx < len(sys.argv):
            # if we encouter non-numeric chunk 
            if not sys.argv[curr_command_idx].isnumeric():
                # then it must be a last, otherwise the input is invalid
                if sys.argv[curr_command_idx] == "last":
                    is_last = True
                else:
                    raise ValueError()
                # check if there is still a cost change after last, if so record it 
                if curr_command_idx+1 < len(sys.argv):
                    if sys.argv[curr_command_idx+1].isnumeric():
                        update_cost = int(sys.argv[curr_command_idx+1])
                    else:
                        raise ValueError()
                break
            # read two elements in one time, the first one is the neighbor port, the second one is the cost to it
            else:
                if not sys.argv[curr_command_idx].isnumeric() or int(sys.argv[curr_command_idx]) < 1024:
                    raise ValueError()
                if curr_command_idx+1 >= len(sys.argv) or not sys.argv[curr_command_idx+1].isnumeric():
                    raise ValueError()
                neighbor_port = int(sys.argv[curr_command_idx])
                neighbor_cost = int(sys.argv[curr_command_idx+1])
                self.neighbors[neighbor_port] = neighbor_cost
                max_port = max(neighbor_port, max_port)
            curr_command_idx += 2
        return is_last, update_cost, max_port


    '''
    Function: print_table()

    Functionality: prints the current routing table in the desired format
    '''
    def print_table(self):
        print(f"[{time.time()}] Node {self.local_port} Routing Table")
        for destination in sorted(self.routing_table.keys()):
            if destination == self.local_port:
                continue
            # if it is a direct link, do not include the next hop
            if self.routing_table[destination][1] == destination:
                print(f"- ({self.routing_table[destination][0]}) -> Node {destination}")
            else:
                print(f"- ({self.routing_table[destination][0]}) -> Node {destination} ; Next hop -> Node {self.routing_table[destination][1]}")

    '''================================================================='''
    '''                                                                 '''
    '''               End Main Function and Input Parsing               '''
    '''                                                                 '''
    '''================================================================='''




    '''################################################################################################'''
    '''################################################################################################'''



    '''================================================================='''
    '''                                                                 '''
    '''             Distance Vector protocol implementation             '''
    '''                                                                 '''
    '''================================================================='''




    '''
    Function: dv_protocal()

    Functionality: 
        - enter main loop based on distance vector protocal, process the input and output, 
          when there is a change in the distance vector, notify the neighbors
    '''
    def protocol_dv(self):
        # initialize the variables
        self.routing_table = {} # maps a destination to its distance and next hop {destination: (total_cost, next_hop)}
        self.last_time_dv = {} # maps a neighbor to the last time we receive an update from it: {neighbor: last_timestamp}
        self.neighbors_recent_dv = {} # maps neighbor to its most recent distance vector {neighbor: (neighbor.routing_table)}
        self.not_sent_first_msg = True # whether the current node has received an message already
        self.routing_table[self.local_port] = (0, self.local_port)
        for neighbor in self.neighbors:
            self.last_time_dv[neighbor] = 0.0
            self.neighbors_recent_dv[neighbor] = {}
            self.routing_table[neighbor] = (self.neighbors[neighbor], neighbor)

        # if the current node is the last node, initialize by sending distance vector to all neighbors
        if self.is_last:
            self.send_dv()
            # handle the case of updating table
            if self.update_cost != None:
                # start a thread link cost change thread that will be evoked in 30 secs
                change_cost_thread = Timer(LINKCOSTCHANGEDELAY, self.change_cost_dv)
                change_cost_thread.start()
        while True:
            # receive the dv update from neighbors
            # messages will be in the form "distance vector dictionary, timestamp, cost_change"
            raw_message, sender_address = self.node_socket.recvfrom(MAXBUFFERSIZE)
            neighbor_ip, neighbor_port = sender_address
            neighbor_dv, time_stamp, neighbor_costs = eval(raw_message.decode())
            
            # if there is no change in cost and also the message is outdated, discard this message
            if neighbor_costs[self.local_port] == self.neighbors[neighbor_port] and self.last_time_dv[neighbor_port] >= float(time_stamp):
                continue
            # if there is a link cost change, record it
            if neighbor_costs[self.local_port] != self.neighbors[neighbor_port]:
                print(f"[{time_stamp}] Link value message received at Node {self.local_port} from node {neighbor_port}")
                self.neighbors[neighbor_port] = neighbor_costs[self.local_port]
            
            # record the newest neighbor distance vector
            self.last_time_dv[neighbor_port] = float(time_stamp)
            self.neighbors_recent_dv[neighbor_port] = neighbor_dv
            # compute new value using Bellman Ford Equation
            changed = self.compute_dv()

            # if there is a change in the distance vector or this node has not sent anything to its neighbors, 
            # then send the updated distance vector and print the change
            if changed or self.not_sent_first_msg:
                self.not_sent_first_msg = False
                print(f"{time_stamp} Message received at Node {self.local_port} from Node {neighbor_port}")
                self.send_dv()
                self.print_table()

    '''
    Function: change_cost()

    Functionality: 
        - trigger cost change event after designated time, if send the link change to the neighbor.
          if there is also any change in the distance vector, broadcast it to the neighbors
    '''
    def change_cost_dv(self):
        curr_time = time.time()
        print(f"[{curr_time}] Node {self.max_port} cost updated to {self.update_cost}")
        self.neighbors[self.max_port] = self.update_cost
        changed = self.compute_dv()
        self.send_link_change_dv(curr_time, self.max_port)
        if changed:
            self.send_dv()
            self.print_table()

    '''
    Function: send_link_change(curr_time, target_port)

    Input:
        - curr_time: the time stamp generated
        - target_port: the port where there is a link cost change between the current node

    Functionality: 
        - enter main loop based on distance vector protocal, process the input and output, 
          when there is a change in the distance vector, notify the neighbors
    '''
    def send_link_change_dv(self, curr_time, target_port):
        msg = str(self.routing_table) + "," + str(curr_time) + "," + str(self.neighbors)
        self.node_socket.sendto(msg.encode(), (self.IP, target_port))
        print(f"[{curr_time}] Link value message sent from Node {self.local_port} to Node {self.max_port}")

    
    '''
    Function: send_dv()

    Functionality: 
        - send the updated routing table to target neighbors also specifying if there is a cost change, 
        differentiate the behavior for different modes
    '''
    def send_dv(self):
        # send different information based on operating mode
        curr_time = time.time()
        for neighbor_port in self.neighbors:
            # if in normal mode, just send whatever we have
            if self.mode == "r":
                msg = str(self.routing_table) + "," + str(curr_time) + "," + str(self.neighbors)
                self.node_socket.sendto(msg.encode(), (self.IP, neighbor_port))
                print(f"[{curr_time}] Message sent from Node {self.local_port} to Node {neighbor_port}")
            elif self.mode == "p":
                self.poisoned_routing_table = self.routing_table.copy()
                # in the poisoned reverse mode
                # if we need to go to a destination where neighbor_port is the next hop, 
                # delete the information for the destination, it has the same functionality as setting the value to inf
                reversed_dest = None
                keys = list(self.poisoned_routing_table.keys())
                for destination in keys:
                    if destination != neighbor_port and self.poisoned_routing_table[destination][1] == neighbor_port:
                        reversed_dest = destination
                        del self.poisoned_routing_table[destination]
                        # self.poisoned_routing_table[destination] = (sys.maxsize, self.poisoned_routing_table[destination][1])
                msg = str(self.poisoned_routing_table) + "," + str(curr_time) + "," + str(self.neighbors)
                self.node_socket.sendto(msg.encode(), (self.IP, neighbor_port))
                if reversed_dest != None:
                    print(f"[{curr_time}] Message sent from Node {self.local_port} to Node {neighbor_port} with distance to Node {reversed_dest} as inf")
                else:
                    print(f"[{curr_time}] Message sent from Node {self.local_port} to Node {neighbor_port}")
        
    '''
    Function: compute_dv()
    Input: 
        - self.neighbors_recent_dv: the newest distance vector receeived from the neighbors
        - self.neighbors: the cost to direct neighbors
    Output:
        - Boolean: if the current node's distance vector (routing table) has changed

    Functionality: compute the new distance-vector of the current node using Bellman Ford Equation.
    '''
    def compute_dv(self):
        new_routing_table = {self.local_port:(0, self.local_port)}
        # compute the routing table based on the most recent estimation from the neighbors
        for neighbor in self.neighbors:
            for destination in self.neighbors_recent_dv[neighbor]:
                # estimate(currnode, destination) = cost(currnode, neighbor) + cost(neighbor, destination)
                new_estimate = self.neighbors[neighbor] + self.neighbors_recent_dv[neighbor][destination][0]
                curr_estimate = new_routing_table.get(destination, (float("inf"), None))[0]
                if new_estimate < curr_estimate:
                    new_routing_table[destination] = (new_estimate, neighbor)
        changed = False
        # if the known destinations are different, there must be a change in the table
        if len(set(self.routing_table.keys()).symmetric_difference(set(new_routing_table))) != 0:
            changed = True
        # or there are tuples that don't match, then either the cost or next hop changes, also update the table
        else:
            for destination in self.routing_table:
                if destination not in new_routing_table or self.routing_table[destination] != new_routing_table[destination]:
                    changed = True
        # update to the new routing table
        self.routing_table = new_routing_table
        return changed

    
    
    
    '''================================================================='''
    '''                                                                 '''
    '''           End Distance Vector protocol implementation           '''
    '''                                                                 '''
    '''================================================================='''




    '''################################################################################################'''
    '''################################################################################################'''




    '''================================================================='''
    '''                                                                 '''
    '''                Link State protocol implementation               '''
    '''                                                                 '''
    '''================================================================='''

    '''
    Function: protocol_ls()

    Functionality: loop based on link state protocal
    '''
    def protocol_ls(self):
        self.topology_ls = {} # will be an adjacency list: {node: {neighbor1: cost1, neighbor2: cost2,...}}
        self.topology_ls[self.local_port] = self.neighbors.copy()
        self.routing_table = {} # will be updated whenever self.compute_ls() is run, will be the same format as dv vector
        self.update_interval += random.random() 
        self.waiting_to_receive_ls = {} # the nodes that we wants to receive back the LSA to the current node {origin_port : {nodes waiting to receivd}}
        self.last_sequence_number_ls = {} # {origin_port : sequence_number} latest sequence_numberp we see a LSA message sent from origin_port 
        self.parent_ls = {} # {origin_port : parent_port} the parent to which we should send back the LSA from origin_port
        self.activated_ls = False # whether the current node is activated
        self.sequence_number = 0 # current sequence number
        self.computed_first_ls = False
        # compute new routing table after ROUTING_INTERVAL seconds
        compute_thread = Timer(ROUTING_INTERVAL, self.compute_ls)
        # broadcast every self.update_interval time, will only start when we received the first message
        update_thread = Thread(target=self.update_ls)
        # if this is the last node
        if self.is_last:
            self.send_ls()
            self.activated_ls = True
            compute_thread.start()
            update_thread.start()
            # if also there is an update evenet in the current node
            if self.update_cost != None:
                change_thread = Timer(1.2*ROUTING_INTERVAL, target=self.change_cost_ls)
                change_thread.start()

        while True:
            # listening for any message
            raw_message, sender_address = self.node_socket.recvfrom(MAXBUFFERSIZE)
            neighbor_ip, neighbor_port = sender_address
            origin_port, sequence_number, lsa_packet = eval(raw_message.decode())
            
            current_sequence_numbere = self.last_sequence_number_ls.get(origin_port, -1)
            # we check whether the current LSA from origin_port is outdated
            if int(sequence_number) < current_sequence_numbere:
                self.print_outdated_lsa_ls(origin_port, sequence_number, neighbor_port)
            # or it is a current LSA that is circulating, removing the sender from the expected received neighbors
            elif int(sequence_number) == current_sequence_numbere:
                # for safty purpose, only remove if it exists
                if neighbor_port in self.waiting_to_receive_ls[origin_port]:
                    self.waiting_to_receive_ls[origin_port].remove(neighbor_port)
                self.print_outdated_lsa_ls(origin_port, sequence_number, neighbor_port)
            # or is a new LSA from that port
            else:
                # print the message indicating receiving
                print(f"[{time.time()}] LSA of Node {origin_port} with sequence number {sequence_number} received from Node {self.local_port}")
                # check the node is not activated
                if not self.activated_ls:
                    self.activated_ls = True
                    self.send_ls()
                    compute_thread.start()
                    update_thread.start()
                # update the topology table
                changed = self.update_topology_table(origin_port, lsa_packet)

                # if the topology table changed:
                if changed:
                    # print the new network topology
                    self.print_topology_ls()
                    # if it has computed after ROUTING_INTERVAL
                    if self.computed_first_ls:
                        # recompute the routing table using dijkstra and print out te new table
                        self.compute_ls()
                # record that the parent is the neighbor who sends us the lsa packet of origin_port
                self.last_sequence_number_ls[origin_port] = sequence_number
                self.parent_ls[origin_port] = neighbor_port
                # then we are expecting an return of the same LSA packet of origin_port except the one that sends us the packet
                self.waiting_to_receive_ls[origin_port] = set(self.neighbors.keys())
                self.waiting_to_receive_ls[origin_port].remove(neighbor_port)
                # broadcast this lsa packet to all neighbors except the parent
                for neighbor in self.neighbors:
                    if neighbor != neighbor_port:
                        self.node_socket.sendto(raw_message, (self.IP, neighbor))
            # if we received from all nodes where we expect the returning packet, forward back to the parent, except the parent is itself
            if len(self.waiting_to_receive_ls[origin_port]) == 0 and self.parent_ls[origin_port] != self.local_port:
                self.node_socket.sendto(raw_message, (self.IP, self.parent_ls[origin_port]))
            # print(self.topology_ls)

    '''
    Function: change_cost_ls()

    Functionality: 
        - trigger the change cost event, will also trigger recomputation of shortest path
    '''
    def change_cost_ls(self):
        self.neighbors[self.max_port] = self.update_cost
        self.topology_ls[self.local_port][self.max_port] = self.update_cost
        self.send_ls()
        self.print_topology_ls()
        self.compute_ls()


    '''
    Function: update_topology_table(origin_port, lsa_packet)

    Input:
        - origin_port: the port information contaned in the message
        - lsa_packet: the original_port's neighbor costs
    Output:
        - Boolean: whether the topology table has changed or not
    Functionality: 
        - update the ropology table based on the received message
    '''
    def update_topology_table(self, origin_port, lsa_packet):
        changed = False
        if origin_port not in self.topology_ls:
            changed = True
        else:
            for neighbor in lsa_packet:
                if neighbor not in self.topology_ls[origin_port] or self.topology_ls[origin_port][neighbor] != lsa_packet[neighbor]:
                    changed = True
                    break
        self.topology_ls[origin_port] = lsa_packet
        return changed
                
    
    '''
    Function: send_ls()

    Functionality: send its newest table to every neighbor
    '''
    def send_ls(self):
        # message wll be in the form (original_port, time_stamp, self.neighbors)
        self.last_sequence_number_ls[self.local_port] = self.sequence_number
        self.waiting_to_receive_ls[self.local_port] = set(self.neighbors.keys())
        self.parent_ls[self.local_port] = self.local_port
        for neighbor in self.neighbors:
            msg = str(self.local_port) + "," + str(self.sequence_number) + "," + str(self.neighbors)
            self.node_socket.sendto(msg.encode(),(self.IP, neighbor))
        self.sequence_number += 1
        


    '''
    Function: print_outdated_lsa_ls(origin_port, sequence_number, neighbor_port)

    Funtionality: print the message when an outdated packet is received
    '''
    def print_outdated_lsa_ls(self, origin_port, sequence_number, neighbor_port):
        print(f"[{time.time()}] Duplicate LSA packet received, AND DROPPED:")
        print(f"- LSA of node {origin_port}")
        print(f"- Sequence number {sequence_number}")
        print(f"- Received from {neighbor_port}")

            
    '''
    Function: update_ls()

    Functionality: 
        - the thread that broadcast its LSA every self.update_interval seconds
    '''
    def update_ls(self):
        while True:
            time.sleep(self.update_interval) 
            self.send_ls()
    

    '''
    Function: compute_ls()
        - input: self.topology
        - output: routing_table

    Functionality: 
        - computes the routing table using dijkstra's algoirthm based on the network topoloy in self.topology, use 
          priority queue to speed up and achieve O(nlogm)
    '''
    def compute_ls(self):
        # Dijkstra loops
        self.computed_first_ls = True
        prev_hop = {node: None for node in self.topology_ls}
        min_cost = {node: 0 for node in self.topology_ls}
        visited = set()
        # priority queue stores (total_cost, current_node, prevnode)
        pq = [(0, self.local_port, None)]
        while pq:
            path_cost, curr_node, prev = heapq.heappop(pq)
            if curr_node in visited:
                continue
            visited.add(curr_node)
            prev_hop[curr_node] = prev
            min_cost[curr_node] = path_cost
            for next_node in self.topology_ls[curr_node]:
                heapq.heappush(pq, (path_cost + self.topology_ls[curr_node][next_node], next_node, curr_node))
        
        # PROCESS THE NEXT HOP FOR THE TABLE, use a recursive funciton
        def find_next_hop(node):
            if prev_hop[node] == self.local_port:
                return node
            # search all the way till we found that the current node's previous node is self.local_port
            return find_next_hop(prev_hop[node])
        
        # update the table based on the result
        for node in min_cost:
            if node != self.local_port:
                self.routing_table[node] = (min_cost[node], find_next_hop(node))
            else:
                self.routing_table[node] = (0, self.local_port)
        # print the recomputed routing table
        self.print_table()


    '''
    Function: print_topology_ls()
        - input: self.topology

    Functionality: 
        - computes the routing table using dijkstra's algoirthm based on the network topoloy in self.topology, use 
          priority queue to speed up and achieve O(nlogm)
    '''
    def print_topology_ls(self):
        print(f"[{time.time()}] Node {self.local_port} Network topology")
        for node in sorted(self.topology_ls.keys()):
            for neighbor in sorted(self.topology_ls[node].keys()):
                if node < neighbor:
                    print(f"- ({self.topology_ls[node][neighbor]}) from Node {node} to Node {neighbor}")
        

    '''================================================================='''
    '''                                                                 '''
    '''              End Link State protocol implementation             '''
    '''                                                                 '''
    '''================================================================='''


    '''##################################################################'''
    '''##################################################################'''



if __name__ == "__main__":
    Node().main()