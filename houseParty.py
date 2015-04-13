from socket import *
from pickle import *
from select import select
import sys
import os
import math
from random import *
import threading
from time import time

PORT = 12345
BUF_SIZE = 1024
STORE_PATH = 'storedFiles/'

#fileHeader: File class. Currently just headers, designed for future expansion

#name: file name
#size: size, in bytes, of the file or file slice.

#hashVal: integer values used for peer hashing. Determines which peer
#is responsible for knowing the file's location

#isSlice: If None, this is a complete file, otherwise it is a fragment
#Suppose a file is split into fragments 1, 2 and 3, each of which is a third of the file.
#Slice A contains 1 and 2. 
#Slice B contains 2 and 3.
#Slice C contains 1 and 3.

#lastWatch: ip address of the node watching this file. Used for determining if
#the node responsible for knowing this file's location has died.
class fileHeader:
	def __init__(self, name, isSlice = ''):
		self.name = name.split('/')[-1]
		self.path = name[0:-len(self.name)]

		stat = os.stat(name+isSlice)
		self.size = stat.st_size

		self.hashVal = sum([ord(x) for x in self.name])
		self.isSlice = isSlice
		self.lastWatch = None

	def split(self):
		try:
			f = open(self.path+self.name,'rb')
		except:
			return [] #FIXME

		limA = int(math.ceil(self.size/3))
		limB = int(math.ceil(self.size*2/3))

		if not os.access(STORE_PATH,os.F_OK):
			os.mkdir(STORE_PATH)

		#FIXME replace with limited size buffer
		#filename_A holds the first 2/3
		fA = open(STORE_PATH + self.name+'_A','wb')
		f.seek(0)
		buf = f.read(limB)
		fA.write(buf)
		fA.close()

		#filename_B holds the last 2/3
		fB = open(STORE_PATH + self.name+'_B','wb')
		f.seek(limA)
		buf = f.read(self.size - limA)
		fB.write(buf)
		fB.close()

		#filename_C holds the first 1/3 and the last 1/3
		fC = open(STORE_PATH + self.name + '_C','wb')
		f.seek(0)
		buf = f.read(limA)
		fC.write(buf)

		f.seek(limB)
		buf = f.read(self.size - limB)
		fC.write(buf)
		fC.close()

		f.close()

		#Create header objects
		retVal = []
		retVal.append(fileHeader(STORE_PATH + self.name, '_A'))
		retVal.append(fileHeader(STORE_PATH + self.name, '_B'))
		retVal.append(fileHeader(STORE_PATH + self.name, '_C'))
		return retVal

	def getFullPath(self):
		return self.path+self.name+self.isSlice

	def recoverSlice(self,other):
		slices = ['_A','_B','_C']
		slices.remove(self.isSlice)
		slices.remove(other.isSlice)

		sliceToRecover = slices[0]
		recoverFile = open(STORE_PATH+self.name+sliceToRecover,'wb')

		if sliceToRecover == '_A':
			if self.isSlice == '_C':
				recoverFile.write(self.getSliceSection(1))
				recoverFile.write(other.getSliceSection(2))
			else:
				recoverFile.write(other.getSliceSection(1))
				recoverFile.write(self.getSliceSection(2))

		if sliceToRecover == '_B':
			if self.isSlice == '_A':
				recoverFile.write(self.getSliceSection(2))
				recoverFile.write(other.getSliceSection(2))

			else:
				recoverFile.write(other.getSliceSection(2))
				recoverFile.write(self.getSliceSection(2))

		if sliceToRecover == '_C':
			if self.isSlice == '_A':
				recoverFile.write(self.getSliceSection(1))
				recoverFile.write(other.getSliceSection(2))
			else:
				recoverFile.write(other.getSliceSection(1))
				recoverFile.write(self.getSliceSection(2))

		recoverFile.close()
		recoverHeader =  fileHeader(STORE_PATH+self.name, sliceToRecover)
		return recoverHeader

	def recoverFile(self,other):
		recoverFile = open(STORE_PATH+self.name,'wb')

		#Get section 1
		if self.isSlice == '_A' or self.isSlice == '_C':
			recoverFile.write(self.getSliceSection(1))
		else:
			recoverFile.write(other.getSliceSection(1))

		#Get section 2
		if self.isSlice == '_A' or self.isSlice == '_B':
			if self.isSlice == '_A':
				recoverFile.write(self.getSliceSection(2))
			else:
				recoverFile.write(self.getSliceSection(1))

		else:
			if other.isSlice == '_A':
				recoverFile.write(other.getSliceSection(2))
			else:
				recoverFile.write(other.getSliceSection(1))

		#Get section 3
		if self.isSlice == '_B' or self.isSlice == '_C':
			recoverFile.write(self.getSliceSection(2))
		else:
			recoverFile.write(other.getSliceSection(2))

		recoverFile.close()
		recoverHeader = fileHeader(STORE_PATH+self.name)
		return recoverHeader

	def getSliceSection(self, half):
		fid = open(self.getFullPath(),'rb')
		if half == 1:
			buf = fid.read(int(math.ceil(self.size/2)))
		else:
			fid.seek(int(math.ceil(self.size/2)))
			buf = fid.read(self.size - int(math.ceil(self.size/2)))

		fid.close()
		return buf

#Storage location for a file
#Name = fileHeader object
#locations = list of strings, representing IP addresses
class fileLocation:
	def __init__(self, header, locations = []):
		self.header = header
		self.locations = [locations]

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
		self.socketLock = threading.Lock()

		self.redist = False

		if not os.access(STORE_PATH,os.F_OK):
			os.mkdir(STORE_PATH)

		self.createThread('splitFiles',[])

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
				self.createThread('addMe', [myHash])

		else:
			self.randID = randint(0,sys.maxint)
			myHash = hashEntry(self.addr, self.randID, 0)
			self.guestList.append(myHash)
			self.hashList.insert(myHash)

	def run(self):
		while(1):
			#If there's a message, get it
			sockStatus = select([sys.stdin,self.sock],[],[],0)
			if sys.stdin in sockStatus[0]:
				self.handleInterupt()

			elif self.sock in sockStatus[0]:
				with self.socketLock:
					pickMessage = self.sock.recvfrom(BUF_SIZE)

				message = loads(pickMessage[0])

				sender = pickMessage[1]
				command = message[0]
				args = message[1]

				# update the last reply time for sender
				self.updateLastReply(sender[0])

				#Handle messages by type

				#Knock sends back the guest list
				if command == 'knock':
					print 'knock from ' + sender[0]
					reply = ('guestList',self.guestList)
					pickReply = dumps(reply)

					with self.socketLock:
						self.sock.sendto(pickReply,sender)

				#addMe initiates an add request
				if command == 'addMe':
					print 'addMe from '+ sender[0]
					
					self.createThread('addGuest', [message,sender[0]])

				#confirmAdd approves people to be added
				if command == 'confirmAdd':
					if 'addMe' in self.threads:
						self.threads['addMe'][1].append(pickMessage)
						continue

					threadName = 'addGuest_'+args[0]
					if (threadName in self.threads):
						self.threads[threadName][1].append(pickMessage)
					else:
						if (args[1] == 'yes'):
							with self.socketLock:
								args[1] = 'no'
								self.sock.sendto(dumps(message),sender)

				#hello-hello pings w/ timeout
				if command == 'hello':
					threadName = 'hello_'+args
					if threadName in self.threads:
						self.threads[threadName][1].append(message)
					elif args == self.addr:
						with self.socketLock:
							self.sock.sendto(pickMessage[0],sender)

				#Have everyone check if someone is still alive
				if command == 'call':
					threadName = 'call_'+args
					if threadName in self.threads:
						self.threads[threadName][1].append(pickMessage)

					elif ('hello_'+message[1] not in self.threads):
						self.createThread('hello',[args])

				#Add a fileHeader to the file list
				if command == 'holdMyPint':
					threadName = 'takePint_'+args[0].name+'_'+args[1][0]
					if threadName not in self.threads:
						self.createThread('takePint',args)
					else:
						pass #FIXME Not sure if needed

				#Add a file name and slice to the file location list
				if command == 'watchMyPint':
					fileHeader = args
					
					entry = [x for x in self.fileLocations if x.header.name == fileHeader.name and x.header.isSlice == fileHeader.isSlice]
					
					for i in entry:
						self.fileLocations.remove(i)
						
					self.fileLocations.append(fileLocation(fileHeader, sender))

				if command == 'wheresMyPint':
					locations = self.getFileLocations(args)
					#headers = [x for x in self.fileList if x.name == args]
					reply = ('heresYourPint',(args, locations))

					pickReply = dumps(reply)
					with self.socketLock:
						self.sock.sendto(pickReply,pickMessage[1])

				if command == 'passMyPint':
					threadName = 'passPint_'+args[0].name+args[0].isSlice+'_'+args[1][0]
					if threadName not in self.threads:
						self.createThread('passPint', args)

				if command == 'heresYourPint':
					threadName = 'wheresMyPint_' + args[0]
					if threadName in self.threads:
						self.threads[threadName][1].append(args[1])
			else:

				tarList = [x for x in self.guestList if (time()-x.time > 8 or time() - x.time < -1) and x.status == 0] #FIXME
				for tar in tarList:
					if (tar.addr == self.addr):
						tar.time = time()
					else:
						threadName = 'hello_'+tar.addr
						if (threadName not in self.threads):
							self.createThread('hello',[tar.addr])

				callList = [x for x in self.guestList if x.status == 1]
				for call in callList:
					threadName = 'call_'+call.addr
					if (threadName not in self.threads):
						self.createThread('call',[call.addr])

				if self.redist:
					self.createThread('redist',[])
					self.redist = False
				

	def holdMyPint(self, header, addr):
		threadName = threading.current_thread().getName()

		print 'Transfering '+header.name+header.isSlice+' to '+addr

		if header in self.fileList:
			self.fileList.remove(header)

		bindSock = socket()
		bindSock.bind((self.addr,0))
		
		transferAddr = bindSock.getsockname()

		fid = open(header.path + header.name + header.isSlice,'rb')

		message = ('holdMyPint',(header,transferAddr))
		pickMessage = dumps(message)
		with self.socketLock:
			self.sock.sendto(pickMessage,(addr,PORT))

		bindSock.listen(1)
		conn = bindSock.accept()
		transferSock = conn[0]		


		buf = fid.read(header.size)

		transferSock.send(buf)

		bindSock.close()
		transferSock.close()
		fid.close()

		print 'Transfer of '+header.name+header.isSlice+' complete.'

		self.threads.pop(threadName, None)


	def takePint(self, fheader, addr):
		threadName = threading.current_thread().getName()

		print 'Taking ' +fheader.name+fheader.isSlice+' from '+addr[0]

		fheader.path = STORE_PATH

		fid = open(fheader.path + fheader.name + fheader.isSlice,'wb')

		transferSock = socket()
		transferSock.connect(addr)

		dataRecieved = 0
		while dataRecieved < fheader.size:
			buf = transferSock.recv(BUF_SIZE)
			fid.write(buf)
			dataRecieved += len(buf)

		fid.close()
		transferSock.close()
		
		self.fileList.append(fheader)
		self.watchMyPint(fheader)

		print fheader.name+fheader.isSlice+' successfully stored.'

		self.threads.pop(threadName, None)


	def watchMyPint(self, f):
		target = self.hashList.search(f.hashVal)
		f.lastWatch = target.addr
		if target.addr == self.addr:
			entry = [x for x in self.fileLocations if x.header.name == f.name and x.header.isSlice == f.isSlice]
			if entry:
				entry[0].locations = [(self.addr,PORT)]
			else:
				self.fileLocations.append(fileLocation(f, self.addr))
			target = self.hashList.search(self.randID-1)

		message = ('watchMyPint', f)
		pickMessage = dumps(message)
		with self.socketLock:
			self.sock.sendto(pickMessage,(target.addr,PORT))

	def wheresMyPint(self, name):
		threadName = threading.current_thread().getName()
		hashVal = sum([ord(x) for x in name])

		target = self.hashList.search(hashVal)

		bindSock = socket()
		bindSock.bind((self.addr,0))
		bindAddr = bindSock.getsockname()

		bindSock.listen(5)

		locations = []
		pints = []

		message = ('wheresMyPint',name)
		pickMessage = dumps(message)

		with self.socketLock:
			self.sock.sendto(pickMessage,(target.addr,PORT))

		while len(pints) < 2:
			q = self.threads[threadName][1]
			if q:
				reply = q.pop()

				for i in reply:
					print i.locations
					if i.locations[0][0] == self.addr:
						pints.append(i)
					elif i.locations[0][0] in [x.addr for x in self.guestList]:
						message = ('passMyPint',(i.header,bindAddr))
						pickMessage = dumps(message)

						fid = open(STORE_PATH+i.header.name+i.header.isSlice,'wb')

						with self.socketLock:
							self.sock.sendto(pickMessage,i.locations[0])

						conn = bindSock.accept()

						print 'connect'

						dataRecieved = 0
						while dataRecieved < i.header.size:
							buf = conn[0].recv(BUF_SIZE)
							fid.write(buf)
							dataRecieved += len(buf)

						i.header.path = STORE_PATH

						pints.append(i)

		return pints

	def passPint(self, header, addr):
		threadName = threading.current_thread().getName()
		
		fid = open(header.path+header.name+header.isSlice,'rb')

		sock = socket()
		sock.connect(addr)

		buf = fid.read(header.size)
		
		sock.send(buf)

		fid.close()
		sock.close()

		self.threads.pop(threadName,None)


	def addMe(self, profile):
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

		while (time() - delay < 4):
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
		print 'Start a call to '+target
		threadName = threading.current_thread().getName()

		tarEntry = [x for x in self.guestList if x.addr == target]
		if not tarEntry:
			print 'HORROR!'
			return #FIXME
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
				print target+' replied. Ending call'
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

		self.redist = True
		
		self.threads.pop(threadName,None)
		
		

	def updateLastReply(self,addr):
		tarList = [x for x in self.guestList if x.addr == addr]
		for tar in tarList:
			tar.time = time()
			tar.status = 0
		if not tarList:
			pass

	def distributeFiles(self):
		threadName = threading.current_thread().getName()

		partialFiles = [x for x in self.fileList if x.isSlice]
		brokenFiles = []
		guestAddr = [x.addr for x in self.guestList]
		for x in self.fileLocations:
			for y in x.locations:
				if y[0] not in guestAddr:
					brokenFiles.append(x)
					break

		while 'splitFiles' in self.threads:
			pass

		while partialFiles:
			f = partialFiles.pop(0)

			otherFragments = [x for x in partialFiles if x.name == f.name and x.isSlice != f.isSlice and x.isSlice != '']

			if len(otherFragments) == 2:
				neighbors = [x.addr for x in self.guestList if x.addr != self.addr]

				addrA = choice(neighbors)
				neighbors.remove(addrA)
				addrB = choice(neighbors)

				self.watchMyPint(f)

				self.createThread('holdMyPint',[otherFragments[0],addrA])
				self.createThread('holdMyPint',[otherFragments[1],addrB])

				partialFiles.remove(otherFragments[0])
				partialFiles.remove(otherFragments[1])
		
			if f.lastWatch != self.hashList.search(f.hashVal):
				self.watchMyPint(f)

		for f in brokenFiles:
			if self.hashList.search(f.header.hashVal).addr == self.addr:
				print f.header.name + ' is broken. Attempting recovery'
				self.createThread('recoverPint',[f.header.name])

		self.threads.pop(threadName,None)

	def recoverPint(self, name):
		threadName = threading.current_thread().getName()

		pints = self.wheresMyPint(name)

		recoveredSlice = pints[0].header.recoverSlice(pints[1].header)

		pintLocations = [y.locations[0][0] for y in pints]
		neighbors = [x.addr for x in self.guestList if x.addr not in pintLocations]
		newAddr = choice(neighbors)

		if newAddr == self.addr:
			self.fileList.append(recoveredSlice)
			self.watchMyPint(recoveredSlice)
		else:
			self.createThread('holdMyPint',[recoveredSlice,newAddr])
		
		self.threads.pop(threadName,None)

	def getPint(self, name):
		threadName = threading.current_thread().getName()

		pints = self.wheresMyPint(name)

		completeFile = pints[0].header.recoverFile(pints[1].header)

		fid = open(completeFile.path+completeFile.name,'rb')

		buf = fid.read(completeFile.size)
		print buf

		self.threads.pop(threadName,None)

	def splitFiles(self):
		threadName = threading.current_thread().getName()
		for i in self.fileList:
			fsplit = i.split()
			self.fileList.extend(fsplit)

		self.threads.pop(threadName,None)

	def getFileLocations(self, name):
		return [x for x in self.fileLocations if x.header.name == name]

	def createThread(self, function, args):
		threadName = ''
		threadFunc = None

		if function == 'splitFiles':
			threadName = 'splitFiles'
			threadFunc = self.splitFiles
		
		elif function == 'holdMyPint':
			threadName = 'holdMyPint_'+args[0].name+'_'+args[1]
			threadFunc = self.holdMyPint

		elif function == 'wheresMyPint':
			threadName = 'wheresMyPint_'+args[0]
			threadFunc = self.wheresMyPint

		elif function == 'passPint':
			threadName = 'passPint_'+args[0].name+args[0].isSlice+'_'+args[1][0]
			threadFunc = self.passPint

		elif function == 'takePint':
			threadName = 'takePint_'+args[0].name+'_'+args[1][0]
			threadFunc = self.takePint

		elif function == 'hello':
			threadName = 'hello_'+args[0]
			threadFunc = self.hello

		elif function == 'call':
			threadName = 'call_'+args[0]
			threadFunc = self.call
	
		elif function == 'addGuest':
			threadName = 'addGuest_'+args[1]
			threadFunc = self.addGuest

		elif function == 'addMe':
			threadName = 'addMe'
			threadFunc = self.addMe

		elif function == 'redist':
			threadName = 'redist'
			threadFunc = self.distributeFiles

		elif function == 'recoverPint':
			threadName = 'wheresMyPint_'+args[0]
			threadFunc = self.recoverPint

		elif function == 'getPint':
			threadName = threadName = 'wheresMyPint_'+args[0]
			threadFunc = self.getPint

		else:
			return threadName

		self.threads[threadName] = [threading.Thread(None, threadFunc, threadName, args),[]]
		self.threads[threadName][0].start()
		return threadName

	def handleInterupt(self):
		inString = sys.stdin.readline().strip()

		if inString == 'h' or inString == 'help':
			print 'Commands:'
			print 'ls'
			print 'get [name]'

		elif inString == 'ls':
			print ''
			print '------------'
			print 'File Status:'
			print '------------'
			print ''
			print 'Now Holding:'
			for i in self.fileList:
				print i.name+i.isSlice
			print ''
			print 'Now Watching:'
			for i in self.fileLocations:
				print i.header.name + i.header.isSlice + ' at ' + str(i.locations)
			print ''

		elif inString.split(' ')[0] == 'get':
			self.createThread('getPint',[inString.split(' ')[1]])

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
