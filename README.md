# spawned
A simple python module for dealing with sub-processes. Based on [pexpect](https://github.com/pexpect/pexpect).

###### Note 
:information_source: The module is Linux only, since it relies on the following commands:

`bash`, `rm`, `sudo`, `pgrep`, `kill`

and might use specific *bash* syntax internally. 

##### Requirements
- linux_x86_64
- python >= 3.8
- latest `pexpect` version

##### How to use
- install the module:
```
$ sudo apt install git python3-pip  # install git and pip3
$ pip3 install git+https://github.com/remico/spawned.git
```
- use just like any other python module
