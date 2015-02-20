from socket import *

HOST = ''
PORT = 12345
s = socket(AF_INET,SOCK_DGRAM)
s.bind((HOST, PORT))
result = s.recvfrom(1024)
print result
