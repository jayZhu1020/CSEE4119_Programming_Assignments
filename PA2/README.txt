To run the program, on command line:

python3 routenode.py <dv/ls> <r/p> <update-interval> <local-port> <neighbor1-port> <cost-1> ... [last] [<cost-change>]

Several cases that are NOT handled for both cases (might crash severely or might be handled correctly, generally undefeined behavior):
1. Duplicate port for different nodes
2. No last node is declared, or last is declared before some nodes
3. Different nodes run in different protocal (one runs in ls and one runs in dv)
4. Not a connected graph (some nodes are isolated)
5. Cost are different in two directions between two nodes upon user input
6. Nodes not running on the same IP
7. Any command line argument appearing after [last] [<cost-change>]
8. UDP drops packet
9. Socket buffer overflow

Main data structures:
1. each node stores a local copy of {neighbor: cost_to_neighbor}
2. the routing table for both protocol uses the format {destination: (cost, next_hop)}

In dv protocol, all the distance vector for all nodes are stored in a hashmap {neighbor: (neighbor's routing_table)}
then apply bellman-ford algorithm with the information in the hashmap

In ls protocol, all the link costs for all nodes are stored in a hashmap {node: {neighbor1: cost1, neighbor2: cost2,...}}
then apply dijkstra's algorithm with the information in the hashmap

Implementation of sequence number:
In ls protocol, the sequence number is the time to which the packet is sent is a local counter. 
Each time the node broadcasts, it sends the message together with the squence numbere and increment the value.
