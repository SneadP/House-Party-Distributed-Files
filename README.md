# House-Party-Distributed-Files
Let's have a party! Csc 462/562 project 1 EDIT: See below for project 2!

Description:
This will be a simple RAID-like file system implemented over a distributed set of nodes, and written in python.

Project 1 is a scaled-back baseline for project 2. Here, I plan to get things working in the simplest sense. The goal for project 1 is to have the nodes able to communicate, join and leave the network, recover from some types of error, and decide where files aught to go. To simplify this project, I won't be passing actual files, just headers. (Real files for project 2, promise!)

I've called this 'House Party', because that's sort of how I want this system to operate. Lets go down the list of how one behaves at a party. Suppose E is going to a party at A's house, and A,B,C, and D are already there.

-First, E needs A's address, which we assume was passed to him earlier. The IP of A (or any active node) is passed as a parameter at start-up. If the address is NULL, it's time to party alone until others show up!

-Next, having arrived at A's address, E knocks on the door. A will answer the door, and let E know that B, C, and D are already here. He'll pass E the 'guest list' (the current hash table of nodes). E will then produce a random ID number to place himself somewhere in the table. That list will be used to determine who is responsible for knowing the locations of what files.

-E, not wanting to be rude, must then go around the room and say hi to other guests. He'll pass them his ID so they know where he goes in the guest list.

-E is now part of the party. And, since it was BYOB, he brought some files with him. To keep things simple in project 1, we're going to stripe the files so that 3 nodes each have a different 2/3 of any given file. E will take his files, split them up into redundant partial files, and distribute them. 3 functions achieve the file sharing and storage.

-holdMyPint(). Pass some data to another node for them to store. If no one else already has pieces of that file, the holder alone decides who will hold the other pieces. Otherwise, you need consensus only between the other holders, not the whole network. For the moment, we assume that everyone has infinite hands, and will always hold your pint without dropping it.

-watchMyPint(). Using the hash table, find out who is responsible for knowing where a particular file is, and inform them of changes to that file or its location.

-wheresMyPint(). Using the hash table, find out who is responsible for knowing where a particular file is, and ask them who has it. It will then retrieve and re-assemble the file from whoever has your pint.

Last, the system should notice if someone abruptly and rudely leaves, and recover any file pieces he was holding from the remaining two peices of that file, restoring them to a new node, as well as redistributing information about the pints around the room.

Running the program:
Call 'python houseParty.py address [file1 file2...] to run the file system. address should be the IP address of any node already in the network, or None to start a new network. The optional arguments are a list of file names to be introduced to the system and passed from node to node. Note that these need not be actual files. For the time being, only headers are passed and stored.

The fabfile includes a set of functions for two test cases. fab demo1A, demo1B, demo1C and demo1D will initalize nodes without files, to examine the party join and leave behaviors. You can kill and restore nodes as much as you want, but two nodes joining at once may cause issues. There is also no elegant way for a node to leave the network. Crashing them is more fun anyway. fab demo2A, demo2B, demo2C, and demo2D will initialize nodes with some 'files' to see how the system handles file distribution. Crashing these nodes is less fun, because while data distribution works, data recovery is still at about 80%, making entirely non-functional.

Error Handling:
The biggest issue handled by this system is getting consensus among the nodes about when to add and remove nodes. On an add, this is handled by asking all other nodes if they also recognise the new entry, and only after approval is sent from all nodes in a new entry added. On a node failure, the first node to notice a timeout sigals all other members of the network to check on the failed node. Every node then pings the failed node, and if all pings fail the node is declared dead and removed.

Data distribution and retrival, on the other hand, requires no consensus at all. Storage locations are determined by whoever happens to hold a file at a given time, and trackers are determined by hash value. Retrival is then a simple matter of looking up the hash and requesting the file from its holders.

The big issue that I've avoided, and the reason only file headers are passed instead of real files, is the infinite number of failure modes involved in issues and interuption during a file transmission. I hope to tackle these properly for project 2.

PROJECT 2 UPDATE!
-----------------
The general outline of the protocol is the same as in project 1. Below are details of what has changed.

Big changes:
	-Transfers and recovers full files to and from peers
	-Added a command line ui to view peer contents and request file retrieval
	-Corrected numerous issues with file recovery behavior in project 1
	-Streamlined concurrent processes to allow the system to remain consistant while transfering multiple files

System structure:
	-Each peer creates a guest object
	-Each guest object creates a main thread that acts as the message handler, and accepts messages from other peers
	-Each guest object maintains a dictionary, threads, which contains key-value pairs of the form threadName : [threadObject,messageQueue]
	-When the main thread receives a message, it is either handled directly (in cases where handling is simple and non-blocking), or
	the main thread creates a worker to handle the message. If such a worker already exists, main adds the message to the worker's
	message queue instead
	-Worker threads are responsible for removing themselves from the dictionary before exiting
	-Messaging is done in UDP

File Transfering:
	-File transfer is donw with TCP sockets
	-A peer may send the signal 'holdMyPint' to another, along with the address and port of a new TCP socket that is listening for 
	connections. The thread that sends the file must create this socket.
	-The peer that recieves the signal creates a new thread, connects to the provided address, and writes it into the file specified
	by the header information passed
	-The receiving peer then reports its acceptance of the file to the network using watchMyPint

File Recovery:
	-Nodes in charge of watching a file can determine when a node goes down if a file has been broken by that failure
	-When a file is detected to have broken, the watching nodes sends requests download the remaining file fragments
	-Once two of three fragments are recovered, the full file can be reproduced
	-The missing fragment is reproduced from the two others
	-The restored fragment is then passed to a new node in the network

Error Handling:
	-Nodes are designed to expect their peers to fail, therefore node failure is handled by design of the system
	-When nodes die, recovery happens, and the system goes on

Test Cases:
	-Put some files in, start a party, then start killing nodes! Any nodes will do.
	-See the demo video for an example of running and testing
