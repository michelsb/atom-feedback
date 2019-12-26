#!/usr/bin/python

from random import randint
from deepdiff import DeepDiff

import commands
import time
import copy

from keystoneauth1 import loading
from keystoneauth1 import session
import novaclient.client as nclient
import collector_agent

from lib.osmclient.client import Client

class CollectorManager():
    def __init__(self):
        self.hostname = commands.getoutput("hostname")
	self.agent = collector_agent.CollectorAgent()       
        self.new_results = {}
        self.old_results = {}
        self.diff_time = 0.0
        self.firstTime = True    
	self.retry = 3
	self.osmclient = Client(host="compnode1")

    def connect_nova(self):
        try:
            ref_file = open("parameters.txt", "r")
            for line in ref_file:
                field = line.split(':')[0].split()[0]
                if field == 'username':
                    self.username = line.split(':')[1].split()[0]
                elif field == 'password':
                    self.password = line.split(':')[1].split()[0]
                elif field == 'project_name':
                    self.project_name = line.split(':')[1].split()[0]
            self.loader = loading.get_plugin_loader('password')
            self.auth = self.loader.load_from_options(auth_url='http://controller:35357/v3',
                                                      username=self.username,
                                                      password=self.password,
                                                      project_name=self.project_name,
                                                      user_domain_name='default',project_domain_name='default')
            self.sess = session.Session(auth=self.auth)
            self.nova = nclient.Client(2, session=self.sess)
            ref_file.close()
            return True
        except Exception, err:
            #print("Error accessing " + server)
            print("Message   :", err)
            self.nova = None
        return False

    def create_session_nova(self):
        for i in range(0, self.retry):
            print("Trying connect with nova... (" + str(i) + ")")
            if self.connect_nova():
                print("Nova Successfuly Connected!")
                break
            time.sleep(5)
        else:
            print("ERROR: It is not possible establish a connection with nova. Exiting...")
            quit()


    def get_stats_from_server(self):
        server_entry = {'name':self.hostname,'timestamp': 0.0,'cpu_load':0.0,'mem_load':0.0,
                        'pifs':[],'tunifs':[],'cpu_back_queue':[],'virtual_machines':[]}

        # Get remote data from server
        remote_stats = self.agent.get_stats()
        server_entry['timestamp'] = remote_stats['timestamp']
        server_entry['cpu_load'] = remote_stats['cpu_load']
        server_entry['mem_load'] = remote_stats['mem_load']
        server_entry['pifs'] = remote_stats['pifs']
        server_entry['tunifs'] = remote_stats['tunifs']
        server_entry['cpu_back_queue'] = remote_stats['cpu_back_queue']

	nfv_services = self.osmclient.ns.list(filter="operational-status=running")
	vdu_names = []
	vdu_list = {} 
	for ns in nfv_services:
		#if (ns is not None) and (type(ns) is not str):
		if isinstance(ns,dict):
			flt = "nsr-id-ref="+ns["id"]
	        	vnfs = self.osmclient.vnf.list(filter=flt)
        		for vnf in vnfs:
                		for vdu in vnf["vdur"]:
					vdu_list[vdu["name"]] = {}
					vdu_list[vdu["name"]]["ns_name"] = ns["name"]
					vdu_list[vdu["name"]]["ns_id"] = ns["id"]
					vdu_list[vdu["name"]]["vnf_id"] = vnf["id"]
					vdu_names.append(vdu["name"])
		else:
			self.osmclient = Client(host="compnode1")
			break

	try:
            for vm in self.nova.servers.list(search_opts={'host': self.hostname, 'status': 'ACTIVE'}):

                tenant_id = str(vm.tenant_id)
                #vm_id = str(vm.id)
                vm_name = str(vm.name)
                vm_entry = {'name': vm_name, 'tenant_name': tenant_id, 'vifs': [], 'nfv_services': []}

		if vm_name in vdu_names:
			vm_entry["nfv_services"].append(vdu_list[vm_name])

                for interface in vm.interface_list():
                    #vif_entry = {'vif_stats': dict(), 'tap_stats': dict(), 'qvb_stats': dict(), 'qvo_stats': dict()}
                    vif_entry = {'tap_stats': dict(), 'qvb_stats': dict(), 'qvo_stats': dict()}
                    vif_entry['name'] = interface.fixed_ips[0]['ip_address']
                    mac = str(interface.mac_addr)
                    vif_entry['mac'] = mac
                    vif_entry['tap_stats'] = remote_stats['vifs'][mac[3:]]['tap_stats']
                    #vif_entry['vif_stats'] = vif_entry['tap_stats'] # TODO
                    vif_entry['qvb_stats'] = remote_stats['vifs'][mac[3:]]['qvb_stats']
                    vif_entry['qvo_stats'] = remote_stats['vifs'][mac[3:]]['qvo_stats']
                    vm_entry['vifs'].append(vif_entry)

                server_entry['virtual_machines'].append(vm_entry)

        except Exception, err:
            print("Error accessing " + server)
            print("Message   :", err)
            return False

        print("Stats from server " + self.hostname + " captured...")

        self.new_results = server_entry

        return True

    def locate_elem_list (self, list, value):
        for x in list:
            if x['name'] == value:
                return x
        return None

    def diff_int_stats(self,old_stats,new_stats):
        new_stats['rx_dropped'] = round(((new_stats['rx_dropped'] - old_stats['rx_dropped'])/100)/self.diff_time,1)
        new_stats['rx_packets'] = round(((new_stats['rx_packets'] - old_stats['rx_packets'])/100)/self.diff_time,1)
        new_stats['rx_bytes'] = round(((new_stats['rx_bytes'] - old_stats['rx_bytes'])/1000)/self.diff_time,1)
        new_stats['tx_dropped'] = round(((new_stats['tx_dropped'] - old_stats['tx_dropped'])/100)/self.diff_time,1)
        new_stats['tx_packets'] = round(((new_stats['tx_packets'] - old_stats['tx_packets'])/100)/self.diff_time,1)
        new_stats['tx_bytes'] = round(((new_stats['tx_bytes'] - old_stats['tx_bytes'])/1000)/self.diff_time,1)

    def diff_queue_stats(self,old_stats,new_stats):
        new_stats['processed_packets'] = round(((new_stats['processed_packets'] - old_stats['processed_packets'])/100)/self.diff_time,1)
        new_stats['dropped_packets'] = round(((new_stats['dropped_packets'] - old_stats['dropped_packets'])/100)/self.diff_time,1)


    def diff_vm_stats(self, list_old_stats, list_new_stats):
        for elem_new_stats in list_new_stats:
            elem_old_stats = self.locate_elem_list(list_old_stats,elem_new_stats['name'])
            if (elem_old_stats is not None):
                #self.diff_int_stats(elem_old_stats['vif_stats'], elem_new_stats['vif_stats'])
                self.diff_int_stats(elem_old_stats['tap_stats'], elem_new_stats['tap_stats'])
                self.diff_int_stats(elem_old_stats['qvb_stats'], elem_new_stats['qvb_stats'])
                self.diff_int_stats(elem_old_stats['qvo_stats'], elem_new_stats['qvo_stats'])

    def diff_elem_list_stats(self, list_old_stats, list_new_stats, type):
        for elem_new_stats in list_new_stats:
            elem_old_stats = self.locate_elem_list(list_old_stats, elem_new_stats['name'])
            if (elem_old_stats is not None):
                if type == 1:
                    self.diff_int_stats(elem_old_stats, elem_new_stats)
                elif type == 2:
                    self.diff_queue_stats(elem_old_stats, elem_new_stats)
                elif type == 3:
                    self.diff_vm_stats(elem_old_stats['vifs'], elem_new_stats['vifs'])
                else:
                    return None

    def calculate_metrics(self):
        old_server_stats = self.old_results
        new_server_stats = copy.deepcopy(self.new_results)      
        
        if (old_server_stats is not None):
		if (new_server_stats['timestamp'] > old_server_stats['timestamp']):
                    self.diff_time = round((new_server_stats['timestamp'] - old_server_stats['timestamp']),1)
                    new_server_stats['timestamp'] = new_server_stats['timestamp'] * 1000
                    self.diff_elem_list_stats(old_server_stats["pifs"], new_server_stats["pifs"], 1)
                    self.diff_elem_list_stats(old_server_stats["tunifs"], new_server_stats["tunifs"], 1)
		    self.diff_elem_list_stats(old_server_stats["cpu_back_queue"], new_server_stats["cpu_back_queue"], 2)
                    #self.diff_elem_list_stats(old_server_stats["virtual_machines"],new_server_stats["virtual_machines"], 3)
                else:
		    return None

        return new_server_stats		
		
    def get_stats(self):
        self.new_results = {'servers': []}
        self.get_stats_from_server()
                
    def connect(self):        
        self.create_session_nova()
	self.get_stats()
        self.old_results = copy.deepcopy(self.new_results)        

    def get_metrics_from_server(self):
	response = {}
        self.get_stats()
        response = self.calculate_metrics()
 	self.old_results = copy.deepcopy(self.new_results)        
	return response
		
    def generate_messages(self):
	messages = []
	response = self.get_metrics_from_server()
	server_main_msg = {'type_msg': 'server_msg', 'server_name': response['name'],'cpu_load':response['cpu_load'],'mem_load':response['mem_load']}
	messages.append(server_main_msg)
	# Physical Interface messages
	for pif_entry in response['pifs']:
		server_pif_msg = {'type_msg': 'pif_msg', 'server_name': response['name'], 'pif_name':pif_entry['name']}           
		server_pif_msg['rx_dropped'] = pif_entry['rx_dropped']
		server_pif_msg['rx_packets'] = pif_entry['rx_packets']
		server_pif_msg['rx_bytes'] = pif_entry['rx_bytes']
		server_pif_msg['tx_dropped'] = pif_entry['tx_dropped']
		server_pif_msg['tx_packets'] = pif_entry['tx_packets']
		server_pif_msg['tx_bytes'] = pif_entry['tx_bytes']
		messages.append(server_pif_msg)
	# Tunnel Interface messages
        for tunif_entry in response['tunifs']:
                server_tunif_msg = {'type_msg': 'tunif_msg', 'server_name': response['name'], 'tunif_name':tunif_entry['name']}
                server_tunif_msg['rx_dropped'] = tunif_entry['rx_dropped']
                server_tunif_msg['rx_packets'] = tunif_entry['rx_packets']
                server_tunif_msg['rx_bytes'] = tunif_entry['rx_bytes']
                server_tunif_msg['tx_dropped'] = tunif_entry['tx_dropped']
                server_tunif_msg['tx_packets'] = tunif_entry['tx_packets']
                server_tunif_msg['tx_bytes'] = tunif_entry['tx_bytes']
                messages.append(server_tunif_msg)
	# CBQ messages
        for cbq_entry in response['cpu_back_queue']:
                cpu_core_name = "core_"+str(cbq_entry['name'])
		server_cbq_msg = {'type_msg': 'cbq_msg', 'server_name': response['name'], 'core_name':cpu_core_name}
                server_cbq_msg['processed_packets'] = cbq_entry['processed_packets']
                server_cbq_msg['dropped_packets'] = cbq_entry['dropped_packets']                
                messages.append(server_cbq_msg)
	# VM messages
	for vm_entry in response['virtual_machines']:
		vm_main_msg = {'type_msg': 'vm_msg', 'server_name': response['name'],'vm_name': vm_entry['name'],'tenant_id': vm_entry['tenant_name']}
	        messages.append(vm_main_msg)
		for ns_entry in vm_entry['nfv_services']:
			vm_ns_msg = {'type_msg': 'ns_msg','server_name': response['name'],'vm_name': vm_entry['name']}
			vm_ns_msg['ns_name'] = ns_entry['ns_name']
			vm_ns_msg['ns_id'] = ns_entry['ns_id']
			vm_ns_msg['vnf_id'] = ns_entry['vnf_id']
			messages.append(vm_ns_msg)
		for vif_entry in vm_entry['vifs']:
			vm_vif_msg = {'type_msg': 'vif_msg','server_name': response['name'],'vm_name': vm_entry['name']}
			vm_vif_msg['vif_name'] = vif_entry['name']
			vm_vif_msg['mac'] = vif_entry['mac']
			vm_vif_msg['tap_stats'] = vif_entry['tap_stats']
			vm_vif_msg['qvb_stats'] = vif_entry['qvb_stats']
			vm_vif_msg['qvo_stats'] = vif_entry['qvo_stats']
			messages.append(vm_vif_msg)
	return messages
	

    def start_manager(self):
        if self.firstTime:
            self.connect()
            time.sleep(2)
	    self.get_metrics_from_server()
            self.firstTime = False


#if __name__ == '__main__':
#	manager = CollectorManager()
#	manager.start_manager()
#        time.sleep(2)
#	print manager.generate_messages()
#    try:
#        print 'Use Control-C to exit'
#        manager = MiningManager()
#        manager.start_manager()
#        print manager.collect()
#    except KeyboardInterrupt:
#        print 'Exiting'
