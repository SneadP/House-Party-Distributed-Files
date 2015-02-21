from socket import *
from pickle import *
from socket import *
from select import select
import sys
from random import *
import threading

PORT = 12345
BUF_SIZE = 1024

class fileHeader:
	def __init__(self,name):
		self.name = name

	def split(self):
		retVal = []
		retVal.append(self.name + "_A")
		retVal.append(self.name + "_B")
		retVal.append(self.name + "_C")
		return retVal

class hashEntry:
	def __init__(self, ipaddr, randID, status):
		self.addr = ipaddr
		self.randID = randID
		self.status = status

class hashTable:
	def __init__(self):
		self.table = [None] * 256
		self.count = 0

	def insert(self,val):
		i = val.randID % 256
		self.table[i] = val
		self.count += 1

	def delete(self,val):
		if (type(val) is int):
			i = val % 256
			self.table[i] = None
		else:
			i = val.randID % 256
			self.table[i] = None
		self.count -=1

	def search(self,val):
		if (type(va) is int):
			return self.table[val % 256]
		else:
			return self.table[val.randID % 256]
	
class guest:
	def __init__(self, neighbor, fileList):
		print 'Starting Node'
		self.sock = socket(AF_INET,SOCK_DGRAM)
		self.sock.bind(('',PORT))

		self.addr = gethostbyname(gethostname())
		myFiles = [fileHeader(x) for x in fileList]
		print 'My address is '+self.addr

		self.guestList = []
		self.hashList = hashTable()
		self.randID = -1

		self.threads = {}
		self.socketLock = threading.Semaphore()

		if (neighbor is not None):
			print 'Sending knock to ' + neighbor
			message = ('knock',None)
			pickMessage = dumps(message)

			with self.socketLock:
				self.sock.sendto(pickMessage,(neighbor,PORT))
				pickReply = self.sock.recvfrom(BUF_SIZE)
			
			reply = loads(pickReply[0])
			if (reply[0] == 'guestList'):
				print 'Acquired guestList from ' + pickReply[1][0]
				self.guestList = reply[1]
				for i in self.guestList:
					self.hashList.insert(i)

				while (self.randID < -1 or self.randID%256 in [x.randID%256 for x in self.guestList]):
					self.randID = randint(0,sys.maxint)

				myHash = hashEntry(self.addr, self.randID, 1)

				self.addMe(myHash)

				self.guestList.append(myHash)
				self.hashList.insert(myHash)
			else:
				sys.exit(-1)

		else:
			self.randID = randint(0,sys.maxint)
			myHash = hashEntry(self.addr, self.randID, 0)
			self.guestList.append(myHash)
			self.hashList.insert(myHash)

	def run(self):
		while(1):
			if(select([self.sock],[],[],0)):
				with self.socketLock:
					pickMessage = self.sock.recvfrom(BUF_SIZE)

				message = loads(pickMessage[0])
				if (message[0] == 'knock'):
					print 'knock from ' + pickMessage[1][0]
					reply = ('guestList',self.guestList)
					pickReply = dumps(reply)

					with self.socketLock:
						self.sock.sendto(pickReply,pickMessage[1])

				if (message[0] == 'addMe'):
					threadName = 'addGuest'+pickMessage[1][0]
					
					self.threads[threadName] = [threading.Thread(None,self.addGuest,threadName,(message,pickMessage[1][0])),[]]
					self.threads[threadName][0].start()

				if (message[0] == 'confirmAdd'):
					print 'confirmAdd from '+pickMessage[1][0]
					threadName = 'addGuest'+message[1][0]
					if (threadName in self.threads):
						self.threads[threadName][1].append(pickMessage)
					else:
						with self.socketLock:
							message[1][1] = 'no'
							self.sock.sendto(dumps(message),pickMessage[1])


	def holdMyPint(self):
		pass

	def watchMyPint(self):
		pass

	def wheresMyPint(self):
		pass

	def addMe(self,profile):
		approval = []
		message = ('addMe',profile)
		pickMessage = dumps(message)

		for i in self.guestList:
			with self.socketLock:
				self.sock.sendto(pickMessage,(i.addr,PORT))
			print 'Sent addMe to '+i.addr

			approval.append(i.addr)

		while (approval):
			
			with self.socketLock:
				pickReply = self.sock.recvfrom(BUF_SIZE)

			reply = loads(pickReply[0])
			if (reply[0] == 'confirmAdd' and reply[1][0] == self.addr):
				approval.remove(pickReply[1][0])
				print 'Recieved approval from ' + pickReply[1][0]

		print 'Entry is approved! Joining party.'


	def addGuest(self,inMessage,addr):
		print "Adding "+addr
		approval = []
		threadName = threading.current_thread().getName()
		message = ('confirmAdd', [addr,'yes'])
		pickMessage = dumps(message)
		
		for i in self.guestList:
			if (i.addr != self.addr):
				self.sock.sendto(pickMessage,(i.addr,PORT))
					
				print 'Confirming addition of ' + addr+ ' with '+i.addr

				approval.append(i.addr)

		while(approval):
			q = self.threads[threadName][1]
			if (len(q) > 0):
				pickReply = q.pop(0)
				reply = loads(pickReply[0])
				if (reply[1][1] == 'yes' and pickReply[1][0] in approval):
					approval.remove(pickReply[1][0])
					#with self.socketLock:
					self.sock.sendto(pickReply[0],pickReply[1])
				

		#with self.socketLock:
		self.sock.sendto(pickMessage,(addr,PORT))

		print addr+' is approved'

		self.guestList.append(inMessage[1])
		self.hashList.insert(inMessage[1])


def main(argv = None):
	if (argv is None):
		argv = sys.argv

	if (len(argv) < 2):
		sys.exit(-1)
	
	if (argv[1] == 'None'):
		addr = None
	else:
		addr = argv[1]
	files = argv[2:]

	myGuest = guest(addr, files)
	myGuest.run()

if __name__ == "__main__":
	main()
