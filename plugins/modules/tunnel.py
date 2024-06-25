#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2023, eNFence GmbH (info@power-devops.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: tunnel
'''

EXAMPLES = r'''
'''

RETURN = r'''
# possible return values
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.enfence.skytap.plugins.module_utils.helpers import (
  restcall, environment_exists, mkauth, set_state
)

import json
import requests
import logging

def create_tunnel(module):
  url = "tunnels.json"
  req = dict()
  req['source_network_id'] = module.params['network1']
  req['target_network_id'] = module.params['network2']
  timeout = None
  if 'timeout' in module.params and module.params['timeout'] is not None:
    timeout = module.params['timeout']
  status, result = restcall(mkauth(module), 'POST', url, json.dumps(req), timeout=timeout)
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def delete_tunnel(module, tunnel_id):
  url = "/v2/tunnels/%s" % tunnel_id
  status, result = restcall(mkauth(module), 'DELETE', url)
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def list_networks(module, environment):
  url = "/v2/configurations/%s/networks" % (environment['id'])
  status, result = restcall(mkauth(module), 'GET', url)
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def list_environments(module):
  url = "/v2/configurations?scope=me&count=100'"
  status, result = restcall(mkauth(module), 'GET', url)
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def list_tunnels(module):
  tunnels = []
  msg, eresult = list_environments(module)
  if msg != '':
    logging.debug('list_environments: %s, failing' % msg)
    return msg, eresult
  for env in eresult:
    msg, nresult = list_networks(module, env)
    if msg != '':
      logging.debug('list_networks: %s, failing' % msg)
      return msg, nresult
    for net in nresult:
      if len(net['tunnels']) > 0:
        tunnels = tunnels + net['tunnels']
  tid = set()
  tunnels = [x for x in tunnels if x['id'] not in tid and (tid.add(x['id']) or True)]
  return '', tunnels

def run_module():
    module_args = dict(
        state=dict(type='str', required=False, choices=['present', 'absent'], default='present'),
        network1=dict(type='str', required=True),
        network2=dict(type='str', required=True),
        auth=dict(type='dict', required=True),
        timeout=dict(type='int', required=False),
    )

    result = dict(
        changed=False,
        msg='No changes'
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    module.debug('Starting enfence.skytap.tunnel module')

    msg, res = list_tunnels(module)
    if msg != '':
      logging.debug('msg is %s, failing' % msg)
      result['error'] = res
      result['msg'] = msg
      result['rc'] = 1
      logging.debug('fail_json')
      module.fail_json(**result)

    logging.debug('searching for the tunnel')
    tunnel_exists = False
    tunnel_id = -1
    for t in res:
      if t['source_network']['id'] == module.params['network1'] and t['target_network']['id'] == module.params['network2']:
        tunnel_exists = True
        tunnel_id = t['id']
        result['tunnel'] = t
      if t['target_network']['id'] == module.params['network2'] and t['target_network']['id'] == module.params['network1']:
        tunnel_exists = True
        tunnel_id = t['id']
        result['tunnel'] = t
    if module.params['state'] == 'present':
      if tunnel_exists:
        module.exit_json(**result)
      if module.check_mode:
        results['msg'] = 'tunnel between networks will be created'
        module.exit_json(**result)
      result['msg'], rc = create_tunnel(module)
      if result['msg'] != '':
        result['error'] = rc
        result['rc'] = 1
        module.fail_json(**result)
      result['tunnel'] = rc
      result['changed'] = True
      module.exit_json(**result)
    elif module.params['state'] == 'absent':
      if not tunnel_exists:
        module.exit_json(**result)
      if module.check_mode:
        results['msg'] = 'tunnel between networks will be deleted'
        module.exit_json(**result)
      result['msg'], rc = delete_tunnel(module, tunnel_id)
      if result['msg'] != '':
        result['error'] = rc
        result['rc'] = 1
        module.fail_json(**result)
      result['tunnel'] = rc
      result['changed'] = True
      module.exit_json(**result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()

