#!/usr/bin/python

import threading
from json import dumps
from kafka import KafkaProducer
from controller_client import RTP4ClientController

#import collector_manager

class SFCMonProducer():
	def __init__(self):
		self.time = 10
		self.collected_metrics = {}
		self.producer = KafkaProducer(bootstrap_servers=['localhost:9092'],
                         value_serializer=lambda x: 
                         dumps(x).encode('utf-8'))

	def create_manager(self):
		self.manager = RTP4ClientController()
		self.manager.startClientController(["p4sfcmon-vm"])

	def start_get_metrics(self):
		self.collected_metrics = self.manager.get_metrics_from_server()
		self.producer.send('sfcmon-metrics',value=self.collected_metrics)
		threading.Timer(self.time, self.start_get_metrics).start()
	
	def start_send_messages(self):
		messages = self.manager.readSFCMon()
		for message in messages:
			self.producer.send('sfcmon-metrics',value=message)
		threading.Timer(self.time, self.start_send_messages).start()

if __name__ == '__main__':
	try:
		producer = SFCMonProducer()
		producer.create_manager()
		#producer.start_get_metrics()
		producer.start_send_messages()
	except KeyboardInterrupt:
        	print 'Exiting'
