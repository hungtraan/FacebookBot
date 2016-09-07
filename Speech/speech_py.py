#!/usr/bin/env python
import credentials

def speech_to_text_ibm_rest(raw_audio):
	print 'Transcribing...'
	endpoint = 'https://stream.watsonplatform.net/speech-to-text/api/v1/recognize'
	auth = "Basic " + base64.b64encode('%s:%s'%(credentials.IBM_STT_USERNAME, credentials.IBM_STT_PASSWORD))
	headers = {'Content-Type': 'audio/wav',
				'Authorization': auth}
	# return summary[1]['hypothesis']
	payload = {'model': 'en-US_NarrowbandModel',
			   'word_alternatives_threshold':'0.9',
			   'continuous': 'true',
			   'smart_formatting': 'true'
			   }
	r = requests.post(endpoint, data=raw_audio,
		headers=headers, params=payload)
	jsonObject = r.json()
	if 'results' in jsonObject:
		hypothesis = ""
        # empty hypothesis
        if (len(jsonObject['results']) == 0):
        	print "empty hypothesis!"
        # regular hypothesis
        else: 
			# dump the message to the output directory
			for res in jsonObject['results']:
				hypothesis += res['alternatives'][0]['transcript']
	return hypothesis.decode('utf8')



# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Google Cloud Speech API sample application using the REST API for batch
processing."""

# [START import_libraries]
import base64
import json

from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials
# [END import_libraries]


# [START authenticating]
DISCOVERY_URL = ('https://{api}.googleapis.com/$discovery/rest?'
                 'version={apiVersion}')


# Application default credentials provided by env variable
# GOOGLE_APPLICATION_CREDENTIALS
def get_speech_service():
    credentials = GoogleCredentials.get_application_default().create_scoped(
        ['https://www.googleapis.com/auth/cloud-platform'])
    http = httplib2.Http()
    credentials.authorize(http)

    return discovery.build(
        'speech', 'v1beta1', http=http, discoveryServiceUrl=DISCOVERY_URL)
# [END authenticating]


def speech_to_text_google(speech_file):
    """Transcribe the given audio file.
    Args:
        speech_file: the name of the audio file.
        Hung's modification: take in binary raw input
    """
    # [START construct_request]
    # Method 1. Take in file input
    # with open(speech_file, 'rb') as speech: # --> for file
        # Base64 encode the binary audio file for inclusion in the JSON
        # request.
        # speech_content = base64.b64encode(speech.read())

    # Method 2. Take in raw binary input
    # Base64 encode the binary audio file for inclusion in the JSON
    # request.
    speech_content = base64.b64encode(speech_file)

    service = get_speech_service()
    service_request = service.speech().syncrecognize(
        body={
            'config': {
                'encoding': 'LINEAR16',
                'sampleRate': 8000,
                'maxAlternatives': 1,
            },
            'audio': {
                'content': speech_content.decode('UTF-8')
                }
            })
    # [END construct_request]
    # [START send_request]
    response = service_request.execute() # return a dict object
    # [END send_request]
    if 'results' in response:
    	results =  sorted(response['results'], reverse=True)
    	print results
    	final_result = results[0]['alternatives'][0]['transcript']
    else:
		print json.dumps(response)
		final_result = "Sorry I couldn't recognize that"
    return final_result

# Copyright IBM Corp. 2014
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Author: Daniel Bolanos
# Date:   2015

# coding=utf-8
import threading                                 # multi threading
import Queue                                     # queue used for thread syncronization
import requests                                  # python HTTP requests library

# WebSockets 
from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory, connectWS
from twisted.internet import ssl, reactor

class Utils:   

   @staticmethod
   def getAuthenticationToken(hostname, serviceName, username, password):
      
      uri = hostname +  "/authorization/api/v1/token?url=" + hostname + '/' + serviceName + "/api" 
      uri = uri.replace("wss://", "https://");
      uri = uri.replace("ws://", "https://");
      resp = requests.get(uri, auth=(username, password), verify=False, headers= {'Accept': 'application/json'}, 
                          timeout= (30, 30))
      # print resp.text
      jsonObject = resp.json()
      return jsonObject['token']


class WSInterfaceFactory(WebSocketClientFactory):

   def __init__(self, queue, summary, contentType, model, url=None, headers=None, debug=None):

      WebSocketClientFactory.__init__(self, url=url, headers=headers)   
      self.queue = queue
      self.summary = summary
      self.contentType = contentType
      self.model = model
      self.queueProto = Queue.Queue()

      self.openHandshakeTimeout = 10
      self.closeHandshakeTimeout = 10

      # start the thread that takes care of ending the reactor so the script can finish automatically (without ctrl+c)
      endingThread = threading.Thread(target=self.endReactor, args= ())
      endingThread.daemon = True
      endingThread.start()
   
   def prepareUtterance(self):

      try:
         utt = self.queue.get_nowait()
         self.queueProto.put(utt)
         return True
      except Queue.Empty:
         # print "getUtterance: no more utterances to process, queue is empty!"
         return False

   def endReactor(self):

      self.queue.join() # Block until all tasks in queue are done
      print "about to stop the reactor!"
      reactor.stop()

   # this function gets called every time connectWS is called (once per WebSocket connection/session)
   def buildProtocol(self, addr):

      try:
         utt = self.queueProto.get_nowait()
         proto = WSInterfaceProtocol(self, self.queue, self.summary, self.contentType)         
         proto.setUtterance(utt)
         return proto 
      except Queue.Empty:
         print "queue should not be empty, otherwise this function should not have been called"
         return None

# WebSockets interface to the STT service
# note: an object of this class is created for each WebSocket connection, every time we call connectWS
class WSInterfaceProtocol(WebSocketClientProtocol):

   def __init__(self, factory, queue, summary, contentType):
      self.factory = factory
      self.queue = queue
      self.summary = summary
      self.contentType = contentType 
      self.packetRate = 20
      self.listeningMessages = 0
      self.timeFirstInterim = -1
      self.bytesSent = 0
      self.chunkSize = 2000    # in bytes
      super(self.__class__, self).__init__()
      # print "contentType: " + str(self.contentType) + " queueSize: " + str(self.queue.qsize())

   def setUtterance(self, utt):

      self.uttNumber = utt[0]
      self.uttFilename = utt[1]
      self.summary[self.uttNumber] = {"hypothesis":"",
                                      "status":{"code":"", "reason":""}}
      
   # helper method that sends a chunk of audio if needed (as required what the specified pacing is)
   def maybeSendChunk(self,data):

      def sendChunk(chunk, final=False):
         self.bytesSent += len(chunk)
         self.sendMessage(chunk, isBinary = True)
         if final: 
            self.sendMessage(b'', isBinary = True)

      if (self.bytesSent+self.chunkSize >= len(data)):        
         if (len(data) > self.bytesSent):
            sendChunk(data[self.bytesSent:len(data)],True)
            return
      sendChunk(data[self.bytesSent:self.bytesSent+self.chunkSize])
      self.factory.reactor.callLater(0.01, self.maybeSendChunk, data=data)
      return

   def onConnect(self, response):
      pass
      # print "onConnect, server connected: {0}".format(response.peer)
   
   def onOpen(self):
      data = {"action" : "start", "content-type" : str(self.contentType), "continuous" : True, "interim_results" : True, "inactivity_timeout": 600}
      data['word_confidence'] = True
      data['timestamps'] = True
      data['max_alternatives'] = 3
      # send the initialization parameters
      self.sendMessage(json.dumps(data).encode('utf8'))

      # start sending audio right away (it will get buffered in the STT service)
      # print self.uttFilename
      f = open(str(self.uttFilename),'rb')
      self.bytesSent = 0
      dataFile = f.read()
      self.maybeSendChunk(dataFile)
      
   def onMessage(self, payload, isBinary):

      if isBinary:
         # print("Binary message received: {0} bytes".format(len(payload)))     
         pass    
      else:
         # print(u"Text message received: {0}".format(payload.decode('utf8')))  

         # if uninitialized, receive the initialization response from the server
         jsonObject = json.loads(payload.decode('utf8'))
         if 'state' in jsonObject:
            self.listeningMessages += 1
            if (self.listeningMessages == 2):
               # close the connection
               self.sendClose(1000)
               
         # if in streaming 
         elif 'results' in jsonObject:
            jsonObject = json.loads(payload.decode('utf8'))            
            hypothesis = ""
            # empty hypothesis
            if (len(jsonObject['results']) == 0):
               print "empty hypothesis!"
            # regular hypothesis
            else: 
               # dump the message to the output directory
               jsonObject = json.loads(payload.decode('utf8'))
               
               hypothesis = jsonObject['results'][0]['alternatives'][0]['transcript']
               bFinal = (jsonObject['results'][0]['final'] == True)
               if bFinal:
                  # print "final hypothesis: \"" + hypothesis + "\""
                  self.summary[self.uttNumber]['hypothesis'] += hypothesis
               # else:
                  # print "interim hyp: \"" + hypothesis + "\""

   def onClose(self, wasClean, code, reason):

      print("WebSocket connection closed: {0}".format(reason), "code: ", code, "clean: ", wasClean, "reason: ", reason)
      self.summary[self.uttNumber]['status']['code'] = code
      self.summary[self.uttNumber]['status']['reason'] = reason
      
      # create a new WebSocket connection if there are still utterances in the queue that need to be processed
      self.queue.task_done()

      if self.factory.prepareUtterance() == False:
         return

      # SSL client context: default
      if self.factory.isSecure:
         contextFactory = ssl.ClientContextFactory()
      else:
         contextFactory = None
      connectWS(self.factory, contextFactory)

def speech_to_text_ibm(file_path):
   # add audio files to the processing queue
   q = Queue.Queue()
   q.put((1,file_path))

   hostname = "stream.watsonplatform.net"   
   headers = {}
   
   credentials = ['c224d410-abd8-4783-97a7-02ff3feb6d3c','sVDa2MAL4gQU']
   model = 'en-US_NarrowbandModel'
   contentType = 'audio/wav'
   threads = '10'
   
   # authentication header
   string = credentials[0] + ":" + credentials[1]
   headers["Authorization"] = "Basic " + base64.b64encode(string)

   # create a WS server factory with our protocol
   url = "wss://" + hostname + "/speech-to-text/api/v1/recognize?model=" + model

   summary = {}
   factory = WSInterfaceFactory(q, summary, contentType, model, url, headers, debug=False)
   factory.protocol = WSInterfaceProtocol

   print 'Transcribing...'
   for i in range(min(int(threads),q.qsize())):
      factory.prepareUtterance()

      # SSL client context: default
      if factory.isSecure:
         contextFactory = ssl.ClientContextFactory()
      else:
         contextFactory = None
      connectWS(factory, contextFactory)

   reactor.run()
   return summary[1]['hypothesis']


# Testing response time between services
# from timeit import default_timer as timer
# file_path = './converted/13635218_10209465570533683_1943824153_n.wav'

# start = timer()
# print speech_to_text_offline(file_path)
# end = timer()
# print('Offlines: ', end-start)

# start = timer()
# print speech_to_text_ibm_rest(file_path)
# end = timer()
# print('IBM: ', end-start)

# start = timer()
# print speech_to_text_google(file_path)
# end = timer()
# print('Google: ', end-start)