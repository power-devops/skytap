#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2023, eNFence GmbH (info@power-devops.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: environment

short_description: manage Skytap environments
version_added: "1.0.0"

description: This module creates/deletes/starts or stops a Skytap environment.

options:
    name:
        description: name of the environment.
        required: true
        type: str
    state:
        description:
          - Desired state of the environment.
          - If the I(state) is C(list), all environments will be listed. The I(name) is ignored in this case.
        required: true
        type: str
        choices: [ present, absent, running, stopped, halted, reset, list ]
    description:
        description: Description of the environment.
        required: false
        type: str
    internet:
        description: If true, outbound internet is disabled for VMs in this environment. Note that VMs with public IPs or published services will still be exposed to the Internet.
        required: false
        type: bool
    lock:
        description: If true, the environment is locked to prevent changes or deletion. Only the environment owner or an administrator can change this value.
        required: false
        type: bool
    local_routing:
        description: If true, different subnets within an environment can communicate with each other.
        required: false
        type: bool
    routable:
        description: Indicates whether networks within the environment can route traffic to one another.
        required: false
        type: bool
    shutdown_at_time:
        description: The date and time that the environment will be automatically shut down.
        required: false
        type: str
    shutdown_on_idle:
        description: The number of seconds an environment can be idle before it’s automatically shut down.
        required: false
        type: str
    suspend_at_time:
        description: The date and time that the environment will be automatically suspended.
        required: false
        type: str
    suspend_on_idle:
        description: The number of seconds an environment can be idle before it’s automatically suspended.
        required: false
        type: int
    template:
        description: Template ID to create an environment. Required if new environment is created.
        required: false
        type: str
    auth:
        description: Authentication data to Skytap API. Must container two fields: I(username) and I(token).
        required: true
        type: dict
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

def _create_req(module, environment):
  req = dict()
  if 'description' in module.params and module.params['description'] is not None and module.params['description'] != '':
    if 'description' not in environment or environment['description'] is None or environment['description'] != module.params['description']:
      req['description'] = module.params['description']
  if 'internet' in module.params and module.params['internet'] is not None:
    if 'disable_internet' not in environment or environment['disable_internet'] is None or environment['disable_internet'] != module.params['internet']:
      req['disable_internet'] = module.params['internet']
  if 'lock' in module.params and module.params['lock'] is not None:
    if 'environment_locked' not in environment or environment['environment_locked'] is None or environment['environment_locked'] != module.params['lock']:
      req['environment_locked'] = module.params['lock']
  if 'local_routing' in module.params and module.params['local_routing'] is not None:
    if 'prefer_local_routing' not in environment or environment['prefer_local_routing'] is None or environment['prefer_local_routing'] != module.params['lock']:
      req['prefer_local_routing'] = module.params['local_routing']
  if 'routable' in module.params and module.params['routable'] is not None:
    if 'routable' not in environment or environment['routable'] is None or environment['routable'] != module.params['routable']:
      req['routable'] = module.params['routable']
  if 'shutdown_at_time' in module.params and module.params['shutdown_at_time'] is not None:
    if 'shutdown_at_time' not in environment or environment['shutdown_at_time'] is None or environment['shutdown_at_time'] != module.params['shutdown_at_time']:
      req['shutdown_at_time'] = module.params['shutdown_at_time']
  if 'shutdown_on_idle' in module.params and module.params['shutdown_on_idle'] is not None:
    if 'shutdown_on_idle' not in environment or environment['shutdown_on_idle'] is None or environment['shutdown_on_idle'] != module.params['shutdown_on_idle']:
      req['shutdown_on_idle'] = module.params['shutdown_on_idle']
  if 'suspend_at_time' in module.params and module.params['suspend_at_time'] is not None:
    if 'suspend_at_time' not in environment or environment['suspend_at_time'] is None or environment['suspend_at_time'] != module.params['suspend_at_time']:
      req['suspend_at_time'] = module.params['suspend_at_time']
  if 'suspend_on_idle' in module.params and module.params['suspend_on_idle'] is not None:
    if 'suspend_on_idle' not in environment or environment['suspend_on_idle'] is None or environment['suspend_on_idle'] != module.params['suspend_on_idle']:
      req['suspend_on_idle'] = module.params['suspend_on_idle']
  return req

def create_environment(module):
  if 'template' not in module.params or module.params['template'] is None or module.params['template'] == '':
    return 'No template ID is specified. Cannot create a new environment', None
  req = dict()
  req['template_id'] = module.params['template']
  req['name'] = module.params['name']
  status, result = restcall(mkauth(module), 'POST', '/v1/configurations', json.dumps(req))
  if status != requests.codes.ok:
    return 'Return code is %s. Environment is not created.' % status, result
  # update environment according to its configuration
  if 'id' in result and result['id'] is not None and result['id'] != '':
    req = _create_req(module, result)
    if len(req) != 0:
      url = "/v1/configurations/%s" % result['id']
      status, result = restcall(mkauth(module), 'PUT', url, json.dumps(req))
      if status != requests.codes.ok:
        return 'Return code is %s. Environment is created but not updated according to the configuration' % status, result
    if module.params['state'] != 'present' and result['runstate'] != module.params['state']:
      status, result = set_state(module, result['id'], module.params['state'])
      if status != requests.codes.ok:
        return 'Return code is %s. Environment is created but not %s' % (status, module.params['state']), result
    return '', result
  else:
    return 'Environment is created but its ID is not found', result

def update_environment(module, environment):
  changed = False
  result = environment
  req = _create_req(module, environment)
  if len(req) != 0:
    if wait_ready(module, environment['id']) == -1:
      return changed, 'Environment is not ready', result
    url = "/v1/configurations/%s" % result['id']
    status, result = restcall(mkauth(module), 'PUT', url, json.dumps(req))
    changed = True
    if status != requests.codes.ok:
      return changed, 'Return code is %s. Environment is created but not updated according to the configuration' % status, result
  if module.params['state'] != 'present' and environment['runstate'] != module.params['state']:
      status, result = set_state(module, result['id'], module.params['state'])
      if status != requests.codes.ok:
        return changed, 'Return code is %s. Environment exists but is not %s' % (status, module.params['state']), result
      changed = True
  return changed, '', result

def delete_environment(module, environment):
  if wait_ready(module, environment['id']) == -1:
    return changed, 'Environment is not ready', result
  url = "/v1/configurations/%s" % environment['id']
  status, result = restcall(mkauth(module), 'DELETE', url)
  if status != requests.codes.ok:
    return 'Return code is %s. Environment is not deleted' % status, result
  return '', result

def list_environments(module):
  url = "/v2/configurations?scope=me&count=100'"
  status, result = restcall(mkauth(module), 'GET', url)
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def run_module():
    module_args = dict(
        name=dict(type='str', required=True),
        state=dict(type='str', required=False, choices=['present', 'running', 'stopped', 'halted', 'reset', 'absent', 'list'], default='present'),
        description=dict(type='str', required=False),
        internet=dict(type='bool', required=False),
        lock=dict(type='bool', required=False),
        local_routing=dict(type='bool', required=False),
        routable=dict(type='bool', required=False),
        shutdown_at_time=dict(type='str', required=False),
        shutdown_on_idle=dict(type='int', required=False),
        suspend_at_time=dict(type='str', required=False),
        suspend_on_idle=dict(type='int', required=False),
        template=dict(type='str', required=False),
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

    module.debug('Starting enfence.skytap.environment module')

    env_info, exists = environment_exists(module, module.params['name'])
    if env_info is not None and not exists:
      # we've got some error from the underlying API call
      module.fail_json(**result)

    if env_info is not None:
      result['environment'] = env_info

    if module.params['state'] == 'list':
      if module.check_mode:
        results['msg'] = 'all environments will be listed'
        module.exit_json(**result)
      result['msg'], rc = list_environments(module)
      if result['msg'] != '':
        result['error'] = rc
        result['rc'] = 1
        module.fail_json(**result)
      result['environment'] = rc
      module.exit_json(**result)
    elif module.params['state'] == 'running' or module.params['state'] == 'present' or module.params['state'] == 'halted' or module.params['state'] == 'stopped' or module.params['state'] == 'reset':
      if not exists:
        if module.check_mode:
          result['msg'] = 'environment will be created'
          module.exit_json(**result)
        result['msg'], res = create_environment(module)
        if result['msg'] != '':
          result['error'] = res
          module.fail_json(**result)
        result['changed'] = True
        result['environment'] = res
        module.exit_json(**result)
      else:
        # check the differences
        if module.check_mode:
          result['msg'] = 'environment exists and will be updated accordingly'
          module.exit_json(**result)
        result['changed'], result['msg'], res = update_environment(module, env_info)
        if result['msg'] != '':
          result['error'] = res
          module.fail_json(**result)
        result['environment'] = res
        module.exit_json(**result)
    elif module.params['state'] == 'absent':
      if exists:
        if module.check_mode:
          result['msg'] = 'environment will be deleted'
          module.exit_json(**result)
        result['msg'], res = delete_environment(module, env_info)
        if result['msg'] != '':
          result['error'] = res
          module.fail_json(**result)
        result['changed'] = True
        module.exit_json(**result)
      else:
        result['msg'] = 'environment does not exist'
        module.exit_json(**result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()

