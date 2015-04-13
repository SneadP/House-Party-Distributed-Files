The files in this tarball are intended to make it easier to interact
with your GEE slice.  You can use these tools to build a full
experiment environment customized for your own needs.  Included are:

id_rsa
------
The private SSH key for use with your GEE slice.


id_rsa.pub
----------
The public SSH key for use with your GEE slice.


ansible-hosts
-------------
An Ansible inventory file to make it easy to run commands across all
your GEE slivers.  Ansible is a free, open-source utility that is
available for most platforms.  It is very well documented and easy to
use.  For more information on Ansible, see:

http://docs.ansible.com/

Some sample Ansible commands that you can use with your GEE slice:

# To make sure all the slivers are up and you can login:
$ ansible nodes -i ansible-hosts --private-key id_rsa -u root -m ping

# To run the 'uptime' command in parallel on all slivers:
$ ansible nodes -i ansible-hosts --private-key id_rsa -u root -m shell -a "uptime"

# To install the 'iperf' package in all the slivers
$ ansible nodes -i ansible-hosts --private-key id_rsa -u root -m apt -a "name=iperf state=present"


fabfile.py
----------
A simple fabfile for use with Fabric, another open-source utility for
running parallel SSH commands.  A fabfile is just Python code that
defines Fabric "commands" which can be invoked from the shell.  For
more information on Fabric, see: 

http://www.fabfile.org/

The current Fabric commands that you can run:

# To run the 'uptime' command in parallel on all slivers:
$ fab uptime

# To test that all slivers have connectivity to www.yahoo.com:
$ fab pingtest

Use these examples to extend the fabfile according to the needs of
your experiment.


ssh-config
----------
SSH configuration for each sliver in the slice.  You can SSH to any
sliver using the label following the 'Host' definition, e.g.,:

$ ssh -F ssh-config -i id_rsa slice352.pcvm3-1.instageni.metrodatacenter.com

Other commands like scp work in the same way, but it is necessary to
specify the -F and -i options as above.

