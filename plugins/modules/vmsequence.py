#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2023, eNFence GmbH (info@power-devops.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: vmsequence
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

def find_vm(environment, vm):
  for v in environment['vms']:
    if v['name'] == vm:
      return v['id']
  return -1

def build_req(module, environment):
  req = dict()
  req['stages'] = list()
  for r in module.params['stages']:
    s = dict()
    if 'index' in r and r['index'] is not None:
      s['index'] = r['index']
    if 'delay_after_finish_seconds' in r and r['delay_after_finish_seconds'] is not None:
      s['delay_after_finish_seconds'] = r['delay_after_finish_seconds']
    s['vm_ids'] = list()
    if 'vms' in r and r['vms'] is not None and len(r['vms']) > 0:
      for vm in r['vms']:
        id = find_vm(environment, vm)
        if id != -1:
          s['vm_ids'].append(id)
    if len(s['vm_ids']) != 0:
      req['stages'].append(s)
  if len(req['stages']) < 4:
    while len(req['stages']) != 4:
      req['stages'].append(dict())
  if len(req['stages']) > 4:
    return dict()
  return req

def get_sequence(module, environment):
  url = "/v2/configurations/%s/stages.json" % (environment['id'])
  status, result = restcall(mkauth(module), 'GET', url)
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def set_sequence(module, environment):
  changed = False
  url = "/v2/configurations/%s/stages.json" % (environment['id'])
  req = build_req(module, environment)
  status, result = restcall(mkauth(module), 'PUT', url, json.dumps(req))
  if status != requests.codes.ok:
    return changed, 'Return code is %s. Starting sequence was not updated.' % status, result
  changed = True
  return changed, '', result

def run_module():
    module_args = dict(
        state=dict(type='str', required=False, choices=['present', 'absent'], default='present'),
        environment=dict(type='str', required=True),
        stages=dict(type='list', elements=dict, required=False),
        auth=dict(type='dict', required=True),
    )

    result = dict(
        changed=False,
        msg='No changes'
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    module.debug('Starting enfence.skytap.vmsequence module')

    env_info, exists = environment_exists(module, module.params['environment'])
    if env_info is not None and not exists:
      # we've got some error from the underlying API call
      module.fail_json(**result)

    if env_info is not None:
      result['environment'] = env_info
    else:
      result['msg'] = 'Environment %s not found' % module.params['environment']
      result['rc'] = 1
      module.fail_json(**result)

    if module.params['state'] == 'present':
      if module.check_mode:
        results['msg'] = 'vm start sequence in the environment %s will be created' % module.params['environment']
        module.exit_json(**result)
      result['changed'], result['msg'], rc = set_sequence(module, env_info)
      if result['msg'] != '':
        result['error'] = rc
        result['rc'] = 1
        module.fail_json(**result)
      result['vmsequence'] = rc
      module.exit_json(**result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()

