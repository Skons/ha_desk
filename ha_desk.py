import os
import RPi.GPIO as GPIO
import time
import sys
import logging
import requests
import argparse
from pprint import pprint
import psutil
import sys
from subprocess import Popen
import socket

def get_lock(process_name):
    # Without holding a reference to our socket somewhere it gets garbage
    # collected when the function exits
    get_lock._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    try:
        get_lock._lock_socket.bind('\0' + process_name)
    except socket.error:
          sys.exit(process_name + ' is already being executed: exiting.')

get_lock('ha_desk.py')

#parse the arguments
parser = argparse.ArgumentParser()
parser.add_argument('-w', '--powerpin', action='store', dest='powerpin', type=int, help="Power relay GPIO pin", default=11)
parser.add_argument('-p', '--uppin', action='store', dest='uppin', type=int, help="Up relay GPIO pin", default=13)
parser.add_argument('-d', '--downpin', action='store', dest='downpin', type=int, help="Down relay GPIO pin", default=15)
parser.add_argument('-c', '--deskcover', action='store', dest='deskcover', help="The name of the cover that indicates the desk state")
parser.add_argument('-e', '--powerboolean', action='store', dest='powerboolean', help="The name of the boolean that indicates the power state")
parser.add_argument('-u', '--url', action='store', dest='url', help="Url of your homeassistant, i.e. https://homeassistant:8123")
parser.add_argument('-t', '--token', action='store', dest='token', help="Bearer token to authenticate against your home assistant instance")
parser.add_argument('-s', '--sleep', action='store', dest='sleep', type=int, help="Number of seconds to wait until next HA read", default=1)
parser.add_argument('-f', '--log-file', action='store', dest='logfile', help="Log file location")
parser.add_argument('-b', '--debug', action='store_true', dest='debug', help="Show debug logging")
args = parser.parse_args()

#prepare logging stuff
if args.debug:
    loglevel = logging.DEBUG
else: 
    loglevel = logging.INFO

if args.logfile is not None:
    logging.basicConfig(filename=args.logfile,filemode='w',format='%(asctime)s %(name)s %(levelname)s %(message)s',datefmt='%Y-%m-%d %H:%M:%S',level=loglevel)
else:
    logging.basicConfig(level=loglevel)

#show the provided parameters
logging.info('Power pin                  = %s',args.powerpin)
logging.info('Up pin                     = %s',args.uppin)
logging.info('Up down                    = %s',args.downpin)
logging.info('Desk state cover           = %s',args.deskcover)
logging.info('Power state boolean        = %s',args.powerboolean)
logging.info('URL                        = %s',args.url)
logging.info('Sleep                      = %s',args.sleep)
logging.info('Logfile                    = %s',args.logfile)

powerpin = args.powerpin
uppin = args.uppin
downpin = args.downpin
sleeptimeorg = args.sleep
sleeptimeforstop = .25

#ToDo, test the response code (i.e. 401)
def get_desk_state(cover):
    headers = {
	'Authorization': 'Bearer '+args.token,
	'content-type': 'application/json'
}
    try:
        url = args.url + '/api/states/cover.' + cover
        r = requests.get(url, headers=headers)
        responseJSON = r.json()
        logging.debug('Data  = %s', responseJSON)
        return responseJSON
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        logging.error('%s', e)
        return ""

def get_power_state(boolean):
    headers = {
	'Authorization': 'Bearer '+args.token,
	'content-type': 'application/json'
}
    try:
        url = args.url + '/api/states/input_boolean.' + boolean
        r = requests.get(url, headers=headers)
        responseJSON = r.json()
        logging.debug('Data  = %s', responseJSON)
        return responseJSON
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        logging.error('%s', e)
        return ""

GPIO.cleanup()
GPIO.setmode(GPIO.BOARD)
GPIO.setup(powerpin, GPIO.OUT)
GPIO.setup(uppin, GPIO.OUT)
GPIO.setup(downpin, GPIO.OUT)

previousState = 'off'
try:
    while True:
      coverData = get_desk_state(args.deskcover)
      booleanData = get_power_state(args.powerboolean)

      state = 'off'
      if 'state' in coverData and 'state' in booleanData:
        if booleanData['state'] == 'on':
          if coverData['state'] == 'open':
            state = 'up'
          elif coverData['state'] == 'closed':
            state = 'down'

      if state != previousState:
        previousState = state
        logging.info('Desk state switched, state is now %s',state)

      if state is 'up':
        sleeptime = sleeptimeforstop
        GPIO.output(uppin, True)
        GPIO.output(powerpin, True)
      elif state is 'down':
        sleeptime = sleeptimeforstop
        GPIO.output(downpin, True)
        GPIO.output(powerpin, True)
      else:
        sleeptime = sleeptimeorg
        GPIO.output(powerpin, False)
        GPIO.output(uppin, False)
        GPIO.output(downpin, False)

      time.sleep(sleeptime)

except KeyboardInterrupt:
    GPIO.cleanup()
