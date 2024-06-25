#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2023, eNFence GmbH (info@power-devops.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: network
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

def list_networks(module, environment):
  url = "/v2/configurations/%s/networks" % (environment['id'])
  status, result = restcall(mkauth(module), 'GET', url)
  if status != requests.codes.ok:
    return 'Return code is %s' % status, result
  return '', result

def run_module():
    module_args = dict(
        name=dict(type='str', required=True),
        state=dict(type='str', required=False, choices=['present', 'absent', 'list'], default='present'),
        environment=dict(type='str', required=True),
        domain=dict(type='str', required=False),
        gateway=dict(type='str', required=False),
        subnet=dict(type='str', required=False),
        dns1=dict(type='str', required=False),
        dns2=dict(type='str', required=False),
        type=dict(type='str', requried=False, choices=['manual', 'automatic'], default='automatic'),
        nat_subnet=dict(type='str', required=False),
        tunnelable=dict(type='bool', required=False),
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

    module.debug('Starting enfence.skytap.network module')

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
        results['msg'] = 'all networks in the environment %s will be listed' % module.params['environment']
        module.exit_json(**result)
      result['msg'], rc = list_networks(module, env_info)
      if result['msg'] != '':
        result['error'] = rc
        result['rc'] = 1
        module.fail_json(**result)
      result['network'] = rc
      module.exit_json(**result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()

