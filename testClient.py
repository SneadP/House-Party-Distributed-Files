from socket import *

HOST = ''
tar = ('10.0.0.244',12345)
PORT = 12345
s = socket(AF_INET,SOCK_DGRAM)
s.bind((HOST, PORT))
s.sendto('hello',tar)
