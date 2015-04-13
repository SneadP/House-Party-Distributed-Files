from fabric.api import *
env.hosts = [
  "slice352.pcvm3-1.geni.case.edu",
    "slice352.pcvm3-1.instageni.metrodatacenter.com",
    "slice352.pcvm2-2.instageni.rnoc.gatech.edu",
    "slice352.pcvm3-2.instageni.illinois.edu",
    "slice352.pcvm5-7.lan.sdn.uky.edu",
#    "slice352.pcvm3-1.instageni.lsu.edu",
#    "slice352.pcvm2-2.instageni.maxgigapop.net",
#    "slice352.pcvm1-1.instageni.iu.edu",
#    "slice352.pcvm3-4.instageni.rnet.missouri.edu",
#    "slice352.pcvm3-7.instageni.nps.edu",
#    "slice352.pcvm2-1.instageni.nysernet.org", dead on delivery
#    "slice352.pcvm3-11.genirack.nyu.edu",
#    "slice352.pcvm5-1.instageni.northwestern.edu",
#    "slice352.pcvm5-2.instageni.cs.princeton.edu",
#    "slice352.pcvm3-3.instageni.rutgers.edu",
#    "slice352.pcvm1-6.instageni.sox.net",
#    "slice352.pcvm3-1.instageni.stanford.edu",
#    "slice352.pcvm2-1.instageni.idre.ucla.edu",
#    "slice352.pcvm4-1.utahddc.geniracks.net",
#    "slice352.pcvm1-1.instageni.wisc.edu",
  ]

env.key_filename="./id_rsa"
env.use_ssh_config = True
env.ssh_config_path = './ssh-config'

def pingtest():
    run('ping -c 3 www.yahoo.com')

@parallel
def uptime():
    run('uptime')

def ifconfig():
	run ('ifconfig')

@hosts("slice352.pcvm3-1.geni.case.edu")
def demo1A():
        run('python houseParty.py None')

@hosts("slice352.pcvm3-1.geni.case.edu")
def demo2A():
	run ('python houseParty.py None herminator.txt guinness.pdf')

@hosts("slice352.pcvm3-1.instageni.metrodatacenter.com")
def demo1B():
        run('python houseParty.py 10.0.1.26')

@hosts("slice352.pcvm2-2.instageni.rnoc.gatech.edu")
def demo1C():
        run('python houseParty.py 10.2.1.27')

@hosts("slice352.pcvm5-7.lan.sdn.uky.edu")
def demo1D():
        run('python houseParty.py 10.0.1.26')

def version():
        run('python3 -V')

@parallel
def update():
        put('houseParty.py','houseParty.py')

@parallel
def prepDemoFiles():
	prepNodeA()
	prepNodeB()

@hosts("slice352.pcvm3-1.geni.case.edu")
def prepNodeA():
	put('herminator.txt','herminator.txt')
	put('guinness.pdf','guinness.pdf')

@hosts("slice352.pcvm3-1.instageni.metrodatacenter.com")
def prepNodeB():
	pass

@parallel
def clean():
        run('rm *')
