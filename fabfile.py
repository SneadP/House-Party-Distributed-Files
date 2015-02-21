from fabric.api import *
env.hosts = ["slice319.pcvm3-1.geni.case.edu",
#    "slice319.pcvm1-1.geni.it.cornell.edu",  This slice misbehaving
    "slice319.pcvm3-1.instageni.metrodatacenter.com",
    "slice319.pcvm2-2.instageni.rnoc.gatech.edu",
    "slice319.pcvm3-2.instageni.illinois.edu",
#    "slice319.pcvm5-7.lan.sdn.uky.edu",
#    "slice319.pcvm3-1.instageni.lsu.edu",
#    "slice319.pcvm2-2.instageni.maxgigapop.net",
#    "slice319.pcvm1-1.instageni.iu.edu",
#    "slice319.pcvm3-4.instageni.rnet.missouri.edu",
#    "slice319.pcvm3-7.instageni.nps.edu",
#    "slice319.pcvm2-1.instageni.nysernet.org",
#    "slice319.pcvm3-11.genirack.nyu.edu",
#    "slice319.pcvm5-1.instageni.northwestern.edu",
#    "slice319.pcvm5-2.instageni.cs.princeton.edu",
#    "slice319.pcvm3-3.instageni.rutgers.edu",
#    "slice319.pcvm1-6.instageni.sox.net",
#    "slice319.pcvm3-1.instageni.stanford.edu",
#    "slice319.pcvm2-1.instageni.idre.ucla.edu",
#    "slice319.pcvm4-1.utahddc.geniracks.net",
#    "slice319.pcvm1-1.instageni.wisc.edu",
  ]

env.key_filename="./id_rsa"
env.use_ssh_config = True
env.ssh_config_path = './ssh-config'

def pingtest():
	run('ping -c 3 10.0.0.244')

def uptime():
	run('uptime')

def ifconfig():
	run('ifconfig')

@hosts("slice319.pcvm3-1.geni.case.edu")
def demoA():
	run('python houseParty.py None')

@hosts("slice319.pcvm3-1.instageni.metrodatacenter.com")
def demoB():
	run('python houseParty.py 10.0.0.244')

@hosts("slice319.pcvm2-2.instageni.rnoc.gatech.edu")
def demoC():
	run('python houseParty.py 10.2.0.245')

@hosts("slice319.pcvm3-2.instageni.illinois.edu")
def demoD():
	run('python houseParty.py 10.0.0.244')

@parallel
def update():
	put('houseParty.py','houseParty.py')

def clean():
	run('rm *')
