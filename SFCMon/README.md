# SFCMon

## Introduction

Repository for SFCMon, an efficient and scalable monitoring solution to keep track network  ows in SFC-enabled domains.

## Software requirements

The virtualization software is portable and should run on a few OSes:

  * Linux
  * Windows PowerShell 3 or later
  * FreeBSD
  * Mac OS X
  * Solaris

## Obtaining required software

The following applications are required:

  * Vagrant: https://www.vagrantup.com/downloads.html
  * VirtualBox: https://www.virtualbox.org/wiki/Downloads

You will need to build a virtual machine. For this, follow the steps below:

 1. Install VirtualBox;
 2. Install Vagrant (use the site installer even on Linux);
 3. Install Vagrant plugins:
 
        # Install vagrant-disksize plugin.
        vagrant plugin install vagrant-disksize
        
 4. Download or clone the SFCMon repository: 
 
         # Clone the git repo.
         git clone https://github.com/michelsb/SFCMon.git
 
 5. Deploy the VM with vagrant (install all P4 dependencies):
 
         # Go to the appropriated directory.
         cd SFCMon/create-dev-env

         # Deploy the VM with vagrant.
         vagrant up
 
 6. Install Docker inside VM:
	
		# Access the VM: 
         vagrant ssh
		 
		# Update the apt package index:
		 sudo apt-get update

		# Install packages to allow apt to use a repository over HTTPS:
		 sudo apt-get install apt-transport-https ca-certificates curl gnupg-agent software-properties-common

		# Add Docker’s official GPG key:
		 curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

		# Use the following command to set up the stable repository.
		 sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

		# Update the apt package index.
		 sudo apt-get update

		# Install the latest version of Docker Engine - Community and containerd, or go to the next step to install a specific version:
		 sudo apt-get install docker-ce docker-ce-cli containerd.io
		 
		# Install Docker Compose
		 sudo curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
		 sudo chmod +x /usr/local/bin/docker-compose
		 sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
		 docker-compose --version
 
 7. Install the kafka-python package inside VM (Kafka python client that we will use in this tutorial)
 
		# Access the VM: 
         vagrant ssh
		 
		# Install the kafka-python package
		 pip install kafka-python
 
 Other auxiliary commands:

         # Access the VM: 
         vagrant ssh
        
         # Halt the VM: 
         vagrant halt (outside VM)
         sudo shutdown -h now (inside VM)
      
         # Destroy the VM: 
         vagrant destroy

## Custom hash functions

The SFCMon requires custom hash functions that use different unique primes for each stage, so that the same flow can be hashed to multiple slots in the hash table in multiple stages. Below, we describe the operations required to enable the new hash functions.

First, we need to access the VM:

         # Go to the appropriated directory.
         cd SFCMon/create-dev-env

         # Access the VM.
         vagrant ssh

Second, we need to extend behavioral-model (bmv2), a public-domain P4 virtual switch, to enable support for multiple pairwise independent hash functions. For this, we implemented the algorithm MurmurHash35, which yields the 32-bit hash value. Next, we define 22 independent hash functions by just varying the seed of MurmurHash3. Adding these hash functions to the behavioral-model is simple. Please, follow the steps below:

 1. Replace the original simple_switch.cpp for our extended file:

        sudo cp /srv/p4-extensions/simple_switch.cpp ~/behavioral-model/targets/simple_switch/simple_switch.cpp

 2. Once doing this remake bmv2:

        NUM_CORES=`grep -c ^processor /proc/cpuinfo`
        cd ~/behavioral-model
        ./autogen.sh
        ./configure --enable-debugger --with-pi
        make -j${NUM_CORES}
        sudo make install

        # Simple_switch_grpc target
        cd targets/simple_switch_grpc
        ./autogen.sh
        ./configure --with-thrift
        make -j${NUM_CORES}
        sudo make install

Finally, we need to update some p4c files in order to make the new hash functions available for P4 programs. Please, follow the steps below:

 1. Replace the following files for our extending files:

        sudo cp /srv/p4-extensions/v1model.p4 ~/p4c/p4include/v1model.p4
        sudo cp /srv/p4-extensions/v1model.h ~/p4c/frontends/p4/fromv1.0/v1model.h
        sudo cp /srv/p4-extensions/simpleSwitch.cpp ~/p4c/backends/bmv2/simpleSwitch.cpp

 2. Once doing this remake p4c:

        cd ~/p4c
        mkdir -p build
        cd build
        cmake ..
        make -j${NUM_CORES}
        make -j${NUM_CORES} check
        sudo make install

## Usage

For the IETF Hackathon, we implement a Proof-of-Concept (PoC) framework aiming to validate and evaluate the SFCMon. By using our PoC framework, we perform experiments aiming to evaluate the SFCMon regarding its performance and scalability.
* [SFCMon's PoC](./testbed) 

## Cite this work

If you use SFCMon for your research and/or other publications, please cite the following paper to reference our work:

BONFIM, Michel ; DIAS, Kelvin ; FERNANDES , Stenio . [**SFCMon: An Efficient and Scalable Monitoring System for Network Flows in SFC-enabled Domains**](https://sol.sbc.org.br/index.php/wpietf/article/view/6581). In: WORKSHOP PRÉ-IETF (WPIETF), 6. , 2019, Belém. Proceedings of the VI Pre-IETF Workshop. Porto Alegre: Sociedade Brasileira de Computação, july 2019 . ISSN 2595-6388. 

Bibtex:

```bibtex
@inproceedings{wpietf,
 author = {Michel  Bonfim and Kelvin  Dias and Stenio  Fernandes	},
 title = {SFCMon: An Efficient and Scalable Monitoring System for Network Flows in SFC-enabled Domains},
 booktitle = {Proceedings of the VI Pre-IETF Workshop},
 location = {Belém},
 year = {2019},
 keywords = {},
 issn = {2595-6388},
 publisher = {SBC},
 address = {Porto Alegre, RS, Brasil},
 url = {https://sol.sbc.org.br/index.php/wpietf/article/view/6581}
}
```

