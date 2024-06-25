#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2023, eNFence GmbH (info@power-devops.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: vm
'''


EXAMPLES = r'''
'''

RETURN = r'''
# possible return values
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.enfence.skytap.plugins.module_utils.helpers import (
  restcall, environment_exists, mkauth, set_state, wait_ready
)

import json
import requests

def list_vms(module, environment):
  if 'vms' in environment and environment['vms'] is not None:
    return '', environment['vms']
  return '', []

def vm_exists(module, environment):
  if 'vms' not in environment or environment['vms'] is None:
    return False
  for vm in environment['vms']:
    if vm['name'] == module.params['name']:
      return True
  return False

def create_vm(module, environment):
  pass

def update_vm(module, environment):
  ourvm = None
  for vm in environment['vms']:
    if vm['name'] == module.params['name']:
      ourvm = vm
  req = dict()
  req['runstate'] = ''
  if module.params['state'] == 'running':
    req['runstate'] = 'running'
  elif module.params['state'] == 'stopped':
    req['runstate'] = 'stopped'
  if req['runstate'] == '':
    return False, 'State is not known', None
  if wait_ready(module, environment['id']) == -1:
      return False, 'Environment is not ready', None
  status, result = restcall(mkauth(module), 'PUT', '/vms/%s.json' % ourvm['id'], json.dumps(req))
  if status != requests.codes.ok:
    return False, 'Return code %s. VM %s (%s) is not started' % (status, ourvm['name'], ourvm['id']), result
  return True, '', result

def delete_vm(module, environment):
  pass

def run_module():
    module_args = dict(
        name=dict(type='str', required=True),
        state=dict(type='str', required=False, choices=['present', 'absent', 'list', 'running', 'stopped', 'halted', 'reset'], default='present'),
        environment=dict(type='str', required=True),
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

    module.debug('Starting enfence.skytap.vm module')

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

    if module.params['state'] == 'list':
      if module.check_mode:
        results['msg'] = 'all virtual machines in the environment %s will be listed' % module.params['environment']
        module.exit_json(**result)
      result['msg'], rc = list_vms(module, env_info)
      if result['msg'] != '':
        result['error'] = rc
        result['rc'] = 1
        module.fail_json(**result)
      result['vm'] = rc
      module.exit_json(**result)

    if module.params['state'] == 'present' or module.params['state'] == 'running' or module.params['state'] == 'stopped' or module.params['state'] == 'halted' or module.params['state'] == 'reset':
      if not vm_exists(module, env_info):
        if module.check_mode:
          results['msg'] = 'virtual machine will be created'
          module.exit_json(**result)
        result['msg'], vm = create_vm(module, env_info)
        if result['msg'] != '':
          result['error'] = vm
          module.fail_json(**result)
        result['changed'] = True
        result['vm'] = vm
        module.exit_json(**result)
      else:
        if module.check_mode:
          result['msg'] = 'virtual machine will be updated according to the attributes'
          module.exit_json(**result)
        result['changed'], result['msg'], vm = update_vm(module, env_info)
        if result['msg'] != '':
          result['error'] = vm
          module.fail_json(**result)
        result['vm'] = vm
        module.exit_json(**result)
    elif module.params['state'] == 'absent':
      if vm_exists(module, env_info):
        if module.check_mode:
          result['msg'] = 'virtual machine will be deleted'
          module.exit_json(**result)
        result['msg'], vm = delete_vm(module, env_info)
        if result['msg'] != '':
          result['error'] = vm
          module.fail_json(**result)
        result['changed'] = True
        result['vm'] = vm
        module.exit_json(**result)
      else:
        result['msg'] = 'virtual machine does not exist'
        module.exit_json(**result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()

