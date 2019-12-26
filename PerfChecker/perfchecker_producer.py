#!/usr/bin/python

import threading
from json import dumps
from kafka import KafkaProducer
import collector_manager

class PerfCheckerProducer():
	def __init__(self):
		self.time = 10
		self.collected_metrics = {}
		self.producer = KafkaProducer(bootstrap_servers=['controller:9092'],
                         value_serializer=lambda x: 
                         dumps(x).encode('utf-8'))

	def create_manager(self):
		self.manager = collector_manager.CollectorManager()
        	self.manager.start_manager()

	def start_get_metrics(self):
		self.collected_metrics = self.manager.get_metrics_from_server()
		self.producer.send('perfchecker-metrics',value=self.collected_metrics)
		threading.Timer(self.time, self.start_get_metrics).start()
	
	def start_send_messages(self):
		messages = self.manager.generate_messages()
		for message in messages:
			self.producer.send('perfchecker-metrics',value=message)
		threading.Timer(self.time, self.start_send_messages).start()

if __name__ == '__main__':
	try:
		producer = PerfCheckerProducer()
		producer.create_manager()
		#producer.start_get_metrics()
		producer.start_send_messages()
	except KeyboardInterrupt:
        	print 'Exiting'
