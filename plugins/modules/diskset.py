#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2023, eNFence GmbH (info@power-devops.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: diskset
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

def list_disksets(module, environment):
  url = "/v2/configurations/%s.json" % (environment['id'])
  status, result = restcall(mkauth(module), 'GET', url)
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  if 'multi_attach_storage_groups' in result:
    return '', result['multi_attach_storage_groups']
  return '', []

def create_diskset(module, environment):
  url = "/v2/configurations/%s/multi_attach_storage_groups.json" % (environment['id'])
  req = dict()
  req['name'] = module.params['name']
  req['hypervisor'] = 'power'
  status, result = restcall(mkauth(module), 'POST', url, json.dumps(req))
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def delete_disk(module, diskset, disk):
  logging.debug('delete_disk: %s', disk)
  url = "/v2/multi_attach_storage_groups/%s/storage_allocations.json" % diskset['id']
  req = dict()
  if isinstance(disk, set):
    req['allocation_ids'] = list(disk)
  else:
    req['allocation_ids'] = list([disk])
  logging.debug('delete_disk: %s', json.dumps(req))
  status, result = restcall(mkauth(module), 'DELETE', url, json.dumps(req))
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def create_disk(module, diskset, disk):
  url = "/v2/multi_attach_storage_groups/%s/storage_allocations.json" % diskset['id']
  req = dict()
  req['spec'] = dict()
  req['spec']['volume'] = list([disk])
  logging.debug('create_disk: %s', json.dumps(req))
  status, result = restcall(mkauth(module), 'POST', url, json.dumps(req))
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def check_disks(module, environment, diskset):
  result = dict()
  changed = False
  if not 'disks' in module.params or module.params['disks'] is None:
    # no disks are defined
    return '', diskset, changed
  if len(module.params['disks']) == 0 and len(diskset['storage_allocations']) == 0:
    return '', diskset, changed
  checked_ids = set()
  for d in module.params['disks']:
    found = False
    for sa in diskset['storage_allocations']:
      if sa['id'] not in checked_ids:
        if int(sa['size']) == int(d):
          found = True
          checked_ids.add(sa['id'])
          break
    if not found:
      msg, result = create_disk(module, diskset, d)
      if msg != '':
        return msg, result, changed
      changed = True
  unneeded_ids = set()
  for sa in diskset['storage_allocations']:
    if sa['id'] not in checked_ids:
      unneeded_ids.add(sa['id'])
  if len(unneeded_ids) > 0:
    msg, result = delete_disk(module, diskset, unneeded_ids)
    if msg != '':
      return msg, result, changed
    changed = True
  return '', result, changed

def get_vmid(environment, vmname):
  if len(environment['vms']) == 0:
    return ""
  for vm in environment['vms']:
    if vm['name'] == vmname:
      return vm['id']
  return ""

def get_vmname(environment, vmid):
  if len(environment['vms']) == 0:
    return ""
  for vm in environment['vms']:
    if vm['id'] == vmid:
      return vm['name']
  return ""

def attach_vm(module, vm_id, diskset):
  url = "/v2/multi_attach_storage_groups/%s/vm_attachments.json" % (diskset['id'])
  req = dict()
  req['vm_ids'] = list([vm_id])
  logging.debug("attach_vm: %s", json.dumps(req))
  status, result = restcall(mkauth(module), 'POST', url, json.dumps(req))
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def detach_vm(module, vm_id, diskset):
  url = "/v2/multi_attach_storage_groups/%s/vm_attachments.json" % (diskset['id'])
  req = dict()
  req['vm_ids'] = list(vm_id)
  status, result = restcall(mkauth(module), 'DELETE', url, json.dumps(req))
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def check_attach(module, environment, diskset):
  result = dict()
  changed = False
  if not 'vms' in module.params or module.params['vms'] is None:
    # no vms are defined
    return '', diskset, changed
  if len(module.params['vms']) == 0 and len(diskset['vm_attachments']) == 0:
    return '', diskset, changed
  if len(environment['vms']) == 0:
    return 'No VMs in the environment', diskset, changed
  # first check if all vms from our list are attached
  for vm in module.params['vms']:
    vm_id = get_vmid(environment, vm)
    if vm_id == "":
      return 'Virtual machine %s is not found in the environment %s' % (vm, environment['name']), diskset, changed
    found = False
    for att in diskset['vm_attachments']:
      if att == vm_id:
        found = True
    if not found:
      msg, result = attach_vm(module, vm_id, diskset)
      if msg != '':
        return msg, result, changed
      changed = True
  # now check that only vms from our list are attached
  for vm_id in diskset['vm_attachments']:
    vm_name = get_vmname(environment, vm_id)
    if vm_name == "":
      # it shouldn't happen. if it is attached, it must be present in the environment
      return 'Virtual machine with ID %s is attached to the disk set, but not found in the environment' % vm_id, diskset, changed
    found = False
    for vm in module.params['vms']:
      if vm == vm_name:
        found = True
    if not found:
      # the attached vm is not found in the module's list. detach it
      msg, result = detach_vm(module, vm_id, diskset)
      if msg != '':
        return msg, result, changed
      changed = True
  return '', result, changed

def delete_diskset(module, environment, diskset):
  url = "/v2/multi_attach_storage_groups/%s" % diskset['id']
  status, result = restcall(mkauth(module), 'DELETE', url)
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def run_module():
    module_args = dict(
        name=dict(type='str', required=True),
        state=dict(type='str', required=False, choices=['present', 'absent', 'list'], default='present'),
        environment=dict(type='str', required=True),
        disks=dict(type='list', elements='str', required=False),
        vms=dict(type='list', elements='str', required=False),
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

    module.debug('Starting enfence.skytap.diskset module')

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

    result['msg'], disksets = list_disksets(module, env_info)
    if result['msg'] != '':
      result['error'] = disksets
      result['rc'] = 1
      module.fail_json(**result)

    if module.params['state'] == 'list':
      result['diskset'] = disksets
      module.exit_json(**result)
    elif module.params['state'] == 'present':
      for ds in disksets:
        if ds['name'] == module.params['name']:
          result['diskset'] = ds
          if not module.check_mode:
            result['msg'], rc, changed = check_disks(module, env_info, ds)
            result['changed'] = changed
            if result['msg'] != '':
              result['error'] = rc
              result['rc'] = 1
              module.fail_json(**result)
            if changed:
              result['diskset'] = rc
            result['msg'], rc, changed = check_attach(module, env_info, ds)
            if changed:
              result['changed'] = changed
              result['diskset'] = rc
            if result['msg'] != '':
              result['error'] = rc
              result['rc'] = 1
              module.fail_json(**result)
          module.exit_json(**result)
      # create new
      if module.check_mode:
        result['msg'] = 'The diskset will be created'
        module.exit_json(**result)
      result['msg'], rc = create_diskset(module, env_info)
      if result['msg'] != '':
        result['error'] = rc
        result['rc'] = 1
        module.fail_json(**result)
      result['changed'] = True
      result['msg'], rc, changed = check_disks(module, env_info, rc)
      if result['msg'] != '':
        result['error'] = rc
        result['rc'] = 1
        module.fail_json(**result)
      if changed:
        result['diskset'] = rc
      result['msg'], rc, changed = check_attach(module, env_info, rc)
      if result['msg'] != '':
        result['error'] = rc
        result['rc'] = 1
        module.fail_json(**result)
      if changed:
        result['diskset'] = rc
      module.exit_json(**result)
    elif module.params['state'] == 'absent':
      for ds in disksets:
        if ds['name'] == module.params['name']:
          result['diskset'] = ds
          # delete it!
          if module.check_mode:
            result['msg'] = 'The diskset will be deleted'
            module.exit_json(**result)
          result['msg'], rc = delete_diskset(module, env_info, ds)
          if result['msg'] != '':
            result['error'] = rc
            result['rc'] = 1
            module.fail_json(**result)
          result['changed'] = True
          result['diskset'] = rc
          module.exit_json(**result)
      module.exit_json(**result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()

