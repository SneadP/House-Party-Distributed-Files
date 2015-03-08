from socket import *
from pickle import *
from socket import *
from select import select
import sys
from random import *
import threading
from time import time

PORT = 12345
BUF_SIZE = 1024

#File class. Currently just headers, designed for future expansion
class fileHeader:
	def __init__(self,name,hashVal = None, isSlice = None):
		self.name = name
		if hashVal == None:
			self.hashVal = sum([ord(x) for x in self.name])
		else:
			self.hashVal = hashVal
		self.isSlice = isSlice
		self.lastWatch = None

	def split(self):
		retVal = []
		retVal.append(fileHeader(self.name,self.hashVal,'A'))
		retVal.append(fileHeader(self.name,self.hashVal,'B'))
		retVal.append(fileHeader(self.name,self.hashVal,'C'))
		return retVal

class fileLocation:
	def __init__(self,f,locations = []):
		self.f = f
		self.locations = locations

#Entry for a guest list
class hashEntry:
	def __init__(self, ipaddr, randID, status):
		self.addr = ipaddr
		self.randID = randID
		self.status = status
		self.time = time()

#Maintained along with the guest list to find who should have a file's location
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
		if (type(val) is int):
			entries = self.table[:val%256]
			entries = [x for x in entries if x is not None]
			if not entries:
				entries = self.table[val%256:]
				entries = [x for x in entries if x is not None]
			return entries[-1]
		else:
			return self.table[val.randID % 256]
	
class guest:
	def __init__(self, neighbor, fileList):
		print 'Starting Node'
		self.sock = socket(AF_INET,SOCK_DGRAM)
		self.sock.bind(('',PORT))

		self.addr = gethostbyname(gethostname())
		self.fileList = [fileHeader(x) for x in fileList]
		self.fileLocations = []
		print 'My address is '+self.addr

		self.guestList = []
		self.hashList = hashTable()
		self.randID = -1

		self.threads = {}
		self.socketLock = threading.Semaphore()

		self.redist = False

		if (neighbor is not None):
			print 'Sending knock to ' + neighbor
			message = ('knock',None)
			pickMessage = dumps(message)

			with self.socketLock:
				self.sock.sendto(pickMessage,(neighbor,PORT))
				pickReply = self.sock.recvfrom(BUF_SIZE)
			
			reply = loads(pickReply[0])
			if reply[0] == 'guestList':
				print 'Acquired guestList from ' + pickReply[1][0]
				self.guestList = reply[1]
				for i in self.guestList:
					i.time = time()
					self.hashList.insert(i)

				while self.randID < -1 or self.randID%256 in [x.randID%256 for x in self.guestList]:
					self.randID = randint(0,sys.maxint)

				myHash = hashEntry(self.addr, self.randID, 0)

				threadName = 'addMe'
				self.threads[threadName] = [threading.Thread(None,self.addMe,threadName,[myHash]),[]]
				self.threads[threadName][0].start()

		else:
			self.randID = randint(0,sys.maxint)
			myHash = hashEntry(self.addr, self.randID, 0)
			self.guestList.append(myHash)
			self.hashList.insert(myHash)

	def run(self):
		while(1):
			if self.redist:
				threadName = 'redist'
				self.threads[threadName] = [threading.Thread(None,self.distributeFiles,threadName),[]]
				self.threads[threadName][0].start()
				self.redist = False
			
			#If there's a message, get it
			sockStatus = select([self.sock],[],[],0)
			if(sockStatus[0]):
				with self.socketLock:
					pickMessage = self.sock.recvfrom(BUF_SIZE)

				message = loads(pickMessage[0])

				# update the last reply time for sender
				self.updateLastReply(pickMessage[1][0])

				#Handle messages by type
				if (message[0] == 'knock'):
					print 'knock from ' + pickMessage[1][0]
					reply = ('guestList',self.guestList)
					pickReply = dumps(reply)

					with self.socketLock:
						self.sock.sendto(pickReply,pickMessage[1])

				if (message[0] == 'addMe'):
					print 'addMe from '+ pickMessage[1][0]
					threadName = 'addGuest_'+pickMessage[1][0]
					
					self.threads[threadName] = [threading.Thread(None,self.addGuest,threadName,(message,pickMessage[1][0])),[]]
					self.threads[threadName][0].start()


				if (message[0] == 'confirmAdd'):
					print 'confirmAdd from '+pickMessage[1][0]
					if 'addMe' in self.threads:
						self.threads['addMe'][1].append(pickMessage)
						continue

					threadName = 'addGuest_'+message[1][0]
					if (threadName in self.threads):
						self.threads[threadName][1].append(pickMessage)
					else:
						if (message[1][1] == 'yes'):
							with self.socketLock:
								message[1][1] = 'no'
								self.sock.sendto(dumps(message),pickMessage[1])

				if (message[0] == 'hello'):
					threadName = 'hello_'+message[1]

					if (threadName in self.threads):
						self.threads[threadName][1].append(message)
					else:
						with self.socketLock:
							self.sock.sendto(pickMessage[0],pickMessage[1])


				if (message[0] == 'call'):
					threadName = 'call_'+message[1]
					if threadName in self.threads:
						self.threads[threadName][1].append(pickMessage)

					elif ('hello_'+message[1] not in self.threads):
						threadName = 'hello_'+message[1]
						self.threads[threadName] = [threading.Thread(None,self.hello,threadName,[message[1]]),[]]
						self.threads[threadName][0].start()

				if (message[0] == 'holdMyPint'):
					print 'Holding '+message[1].name
					self.fileList.append(message[1])
					self.watchMyPint(message[1])

				if message[0] == 'watchMyPint':
					print 'Watching '+message[1].name+' for '+pickMessage[1][0]
					entry = [x for x in self.fileLocations if x.f == message[1]]
					if entry:
						entry[0].locations.append(pickMessage[1][0])
					else:
						self.fileLocations.append(fileLocation(message[1], pickMessage[1][0]))
				if messasge[0] == 'wheresMyPint':
					entry = [x for x in self.fileList if x.name == message[1]]
					entry.extend([x for x in self.fileLocations if x.f == message[1]])
					if entry:
						messasge = ('heresYourPint', entry[0])
					else:
						message = ('heresYourPint', self.hashList.search(message[1]))
					pickMessage[0] = dumps(message)
					with self.socketLock:
						self.sock.sendto(pickMessage[0],pickMessage[1])
			else:

				tarList = [x for x in self.guestList if (time()-x.time > 10 or time() - x.time < 0) and x.status == 0] #FIXME
				for tar in tarList:
					if (tar.addr == self.addr):
						tar.time = time()
					else:
						threadName = 'hello_'+tar.addr
						if (threadName not in self.threads):
							self.threads[threadName] = [threading.Thread(None,self.hello,threadName,[tar.addr]),[]]
							self.threads[threadName][0].start()

				callList = [x for x in self.guestList if x.status == 1]
				for call in callList:
					threadName = 'call_'+call.addr
					if (threadName not in self.threads):
						self.threads[threadName] = [threading.Thread(None,self.call,threadName,[call.addr]),[]]
						self.threads[threadName][0].start()
				

	def holdMyPint(self, f, addr):
		message = ('holdMyPint',f)
		pickMessage = dumps(message)
		with self.socketLock:
			self.sock.sendto(pickMessage,(addr,PORT))

		print addr+' will hold '+f.name

	def watchMyPint(self, f):
		target = self.hashList.search(f.hashVal)
		message = ('watchMyPint', f)
		pickMessage = dumps(message)
		with self.socketLock:
			self.sock.sendto(pickMessage,(target.addr,PORT))
		f.lastWatch = target.addr

		print target.addr+' will watch '+f.name
		

	def wheresMyPint(self, name):
		threadName = threading.current_thread().getName()
		hashVal = sum([ord(x) for x in name])

		target = self.hashList.searh(hashVal)

		locations = []
		pints = []

		message = ('wheresMyPint',name)
		pickMessage = dumps(message)

		with self.socketLock:
			self.sock.sendto(pickMessage,(target.addr,PORT))

		while len(pints) < 2:
			q = self.threads[threadName][1]
			if q:
				pickReply = q.pop()
				reply = loads(pickReply[0])

				if type(reply[1]) == fileHeader:
					pints.append(reply[1])
				else:
					locations.extend(reply[1])
			for i in locations:
				with self.socketLock:
					self.sock.sendto(pickMessage,(i,PORT))
			locations = []


	def addMe(self,profile):
		threadName = threading.current_thread().getName()
		approval = []
		message = ('addMe',profile)
		pickMessage = dumps(message)

		for i in self.guestList:
			if (i.status == 0):
				with self.socketLock:
					self.sock.sendto(pickMessage,(i.addr,PORT))
				print 'Sent addMe to '+i.addr

				approval.append(i.addr)

		while (approval):
			q = self.threads[threadName][1]
			if q:
				pickReply = q.pop()

				reply = loads(pickReply[0])
				if (reply[0] == 'confirmAdd' and reply[1][0] == self.addr):
					approval.remove(pickReply[1][0])
					print 'Recieved approval from ' + pickReply[1][0]

		print 'Entry is approved! Joining party.'

		self.guestList.append(profile)
		self.hashList.insert(profile)

		if len(self.guestList) >= 3:
			self.redist = True

		self.threads.pop(threadName,None)


	def addGuest(self,inMessage,addr):
		print "Adding "+addr
		approval = []
		threadName = threading.current_thread().getName()
		message = ('confirmAdd', [addr,'yes'])
		pickMessage = dumps(message)
		
		for i in self.guestList:
			if (i.addr != self.addr and i.status == 0):
				with self.socketLock:
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
					with self.socketLock:
						self.sock.sendto(pickReply[0],pickReply[1])
				
		with self.socketLock:
			self.sock.sendto(pickMessage,(addr,PORT))

		print addr+' is approved'

		inMessage[1].time = time()
		self.guestList.append(inMessage[1])
		self.hashList.insert(inMessage[1])

		if (len(self.guestList) >= 3):
			self.redist = True

		self.threads.pop(threadName,None)

	def hello(self, target):
		threadName = threading.current_thread().getName()

		message = ('hello',target)
		pickMessage = dumps(message)
		with self.socketLock:
			self.sock.sendto(pickMessage,(target,PORT))

		delay = time()

		while (time() - delay < 5):
			q = self.threads[threadName][1]
			if q:
				q.pop(0)
				self.updateLastReply(target)

				successes = [x for x in self.guestList if x.addr == target]
				for success in successes:
					success.status = 0
	
				self.threads.pop(threadName,None)
				return True

		fails = [x for x in self.guestList if x.addr == target]
		for failure in fails:
			failure.status = 1

		self.threads.pop(threadName,None)
		return False
		

	def call(self,target):
		threadName = threading.current_thread().getName()

		tarEntry = [x for x in self.guestList if x.addr == target]
		if not tarEntry:
			pass #FIXME
		tarEntry = tarEntry[0]
		

		approval = [x.addr for x in self.guestList if x.addr!= self.addr and x.addr != target]

		message = ('call',target)
		pickMessage = dumps(message)

		for i in approval:
			with self.socketLock:
				self.sock.sendto(pickMessage,(i,PORT))

		while approval:
			q = self.threads[threadName][1]

			if tarEntry.status == 0:
				self.threads.pop(threadName,None)
				return

			elif len(q) > 0:
				pickReply = q.pop()
				if pickReply[1][0] in approval:
					approval.remove(pickReply[1][0])
					with self.socketLock:
						self.sock.sendto(pickReply[0],pickReply[1])

		print target+' failed to respond. Removing from guest list'
		kill = [x for x in self.guestList if x.addr == target]
		for i in kill:
			self.guestList.remove(i)
			self.hashList.delete(i)
		
		self.threads.pop(threadName,None)
		
		

	def updateLastReply(self,addr):
		tarList = [x for x in self.guestList if x.addr == addr]
		for tar in tarList:
			tar.time = time()
			tar.status = 0

	def distributeFiles(self):
		completeFiles = [x for x in self.fileList if not x.isSlice]
		partialFiles = [x for x in self.fileList if x.isSlice]
		
		for f in completeFiles:
			fSplit = f.split()
			self.fileList.remove(f)
			self.fileList.append(fSplit[0])

			neighbors = [x.addr for x in self.guestList if x.addr != self.addr]

			addrA = choice(neighbors)
			neighbors.remove(addrA)
			addrB = choice(neighbors)

			self.watchMyPint(fSplit[0])
			self.holdMyPint(fSplit[1],addrA)
			self.holdMyPint(fSplit[2],addrB)

		for f in partialFiles:
			if f.lastWatch != self.hashList.search(f.hashVal):
				self.watchMyPint(f)


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
