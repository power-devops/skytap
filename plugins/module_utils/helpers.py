# Copyright (c) 2023, eNFence GmbH (info@power-devops.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
from ansible.module_utils.basic import is_executable

__metaclass__ = type

import json
import logging
import requests
import time

# API endpoint for Skytap REST API
API_BASE = 'https://cloud.skytap.com/'
API_HEADERS = {'Accept': 'application/json', 'Content-type': 'application/json'}

import http.client as http_client

def restcall(auth, method, path, data=None, timeout=None):
	http_client.HTTPConnection.debuglevel = 2
	logging.basicConfig(filename='requests.log', encoding='utf-8', level=logging.DEBUG)
	logging.getLogger().setLevel(logging.DEBUG)
	requests_log = logging.getLogger("requests.packages.urllib3")
	requests_log.setLevel(logging.DEBUG)
	requests_log.propagate = True
	logging.debug('data is %s', data)
	try:
		if(method == 'GET'):
			result = requests.get(API_BASE + path, headers=API_HEADERS, auth=auth, timeout=timeout)
		if(method == 'POST'):
			result = requests.post(API_BASE + path, headers=API_HEADERS, data=data, auth=auth, timeout=timeout)
		if(method == 'PUT'):
			result = requests.put(API_BASE + path, headers=API_HEADERS, data=data, auth=auth, timeout=timeout)
		if(method == 'DELETE'):
			result = requests.delete(API_BASE + path, headers=API_HEADERS, allow_redirects=True, data=data, auth=auth, timeout=timeout)

		if len(result.content) > 0:
			return result.status_code, result.json()
		else:
			return result.status_code, None
	except Exception as e:
		return -1, e

def mkauth(module):
	return (module.params['auth']['username'], module.params['auth']['token'])

def environment_exists(module, envname):
	status, result = restcall(mkauth(module), 'GET', '/v2/configurations?scope=me&count=100')
	if status == requests.codes.ok:
		# check that envname exists
		for e in result:
			if e['name'] == envname:
				return e, True
		return None, False
	else:
		return result, False
	return None, False

def wait_ready(module, environment_id, repeat = -1, timeout = 5):
	url = "/v1/configurations/%s" % environment_id
	r = 0
	while r != repeat:
		status, result = restcall(mkauth(module), 'GET', url)
		if status != requests.codes.ok:
			return -1
		if 'runstate' in result and result['runstate'] is not None and result['runstate'] != 'busy':
			return 0
		r = r + 1
		time.sleep(timeout)
	return -1

def set_state(module, environment_id, state):
	url = "/v1/configurations/%s" % environment_id
	if wait_ready(module, environment_id) == -1:
		return -1, None
	req = dict()
	req['runstate'] = state
	return restcall(mkauth(module), 'PUT', url, json.dumps(req))

def set_vm_state(module, environment_id, vm_id, state):
  url = "/v1/vms/%s.json" % vm_id
  if wait_ready(module, environment_id) == -1:
    return -1, None
  req = dict()
  req['runstate'] = state
  return restcall(mkauth(module), 'PUT', url, json.dumps(req))