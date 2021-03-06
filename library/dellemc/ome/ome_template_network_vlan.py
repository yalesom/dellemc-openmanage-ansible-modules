#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Dell EMC OpenManage Ansible Modules
# Version 2.0.9
# Copyright (C) 2020 Dell Inc.

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# All rights reserved. Dell, EMC, and other trademarks are trademarks of Dell Inc. or its subsidiaries.
# Other trademarks may be trademarks of their respective owners.
#


from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: ome_template_network_vlan
short_description: set tagged and untagged vlans to native network card supported by a template.
version_added: "2.9"
description: This module allows to set tagged and untagged vlans to native network card supported by a template.
options:
  hostname:
    description: Target IP Address or hostname.
    required: true
    type: str
  username:
    description: Target username.
    required: true
    type: str
  password:
    description: Target user password.
    required: true
    type: str
  port:
    description: Target HTTPS port.
    default: 443
    type: int
  template_name:
    description:
      - Name of the template.
      - It is mutually exclusive with I(template_id)
    type: str
  template_id:
    description:
      - Id of the template.
      - It is mutually exclusive with I(template_name)
    type: int
  nic_identifier:
    description: Display name of NIC port in the template for vLAN configuration.
    required: true
    type: str
  untagged_networks:
    description: List of untagged networks and their corresponding NIC ports
    elements: dict
    type: list
    suboptions:
      port:
        description: NIC port number of the untagged vLAN.
        required: true
        type: int
      untagged_network_id:
        description:
          - ID of the untagged vLAN
          - Enter 0 to clear the untagged vLAN from the port.
          - This option is mutually exclusive with I(untagged_network_name)
          - To get the vLAN network ID use the API U( https://I(hostname)/api/NetworkConfigurationService/Networks)
        type: int
      untagged_network_name:
        description:
          - name of the vlan for untagging
          - provide 0 for clearing the untagging for this I(port)
          - This parameter is mutually exclusive with I(untagged_network_id)
        type: str
  tagged_networks:
    description: List of tagged vLANs and their corresponding NIC ports.
    type: list
    elements: dict
    suboptions:
      port:
        description: NIC port number of the tagged vLAN
        required: true
        type: int
      tagged_network_ids:
        description:
          - List of IDs of the tagged vLANs
          - Enter [] to remove the tagged vLAN from a port.
          - List of I(tagged_network_ids) is combined with list of I(tagged_network_names) when adding tagged vLANs to a port.
          - To get the vLAN network ID use the API U( https://I(hostname)/api/NetworkConfigurationService/Networks)
        type: list
        elements: int
      tagged_network_names:
        description:
          - List of names of tagged vLANs
          - Enter [] to remove the tagged VLAN from a port.
          - List of I(tagged_network_names) is combined with list of I(tagged_network_ids) when adding tagged vLANs to a port.
        type: list
        elements: str
requirements:
    - "python >= 2.7.5"
author:
    - "Jagadeesh N V(@jagadeeshnv)"
'''

EXAMPLES = r'''
---
- name: Add tagged or untagged vLANs to a template using vLAN ID and name.
  ome_template_network_vlan:
    hostname: "192.168.0.1"
    username: "username"
    password: "password"
    template_id: 78
    nic_identifier: NIC Slot 4
    untagged_networks:
      - port: 1
        untagged_network_id: 127656
      - port: 2
        untagged_network_name: vlan2
    tagged_networks:
      - port: 1
        tagged_network_ids:
          - 12767
          - 12768
      - port: 4
        tagged_network_ids:
          - 12767
          - 12768
        tagged_network_names:
          - vlan3
      - port: 2
        tagged_network_names:
          - vlan4
          - vlan1

- name: Clear the tagged and untagged vlans vLANs from a template.
  ome_template_network_vlan:
    hostname: "192.168.0.1"
    username: "username"
    password: "password"
    template_id: 78
    nic_identifier: NIC Slot 4
    untagged_networks:
      # For removing the untagged vLANs for the port 1 and 2
      - port: 1
        untagged_network_id: 0
      - port: 2
        untagged_network_name: 0
    tagged_networks:
      # For removing the tagged vLANs for port 1, 4 and 2
      - port: 1
        tagged_network_ids: []
      - port: 4
        tagged_network_ids: []
        tagged_network_names: []
      - port: 2
        tagged_network_names: []
'''

RETURN = r'''
---
msg:
  type: str
  description: Overall status of the template vlan operation.
  returned: always
  sample: "Successfully applied the network settings to template"
error_info:
  description: Details of the HTTP Error.
  returned: on HTTP error
  type: dict
  sample: {
        "error": {
            "@Message.ExtendedInfo": [
                {
                    "Message": "Unable to complete the request because
                    TemplateId  does not exist or is not applicable for the
                    resource URI.",
                    "MessageArgs": [
                        "TemplateId"
                    ],
                    "MessageId": "CGEN1004",
                    "RelatedProperties": [],
                    "Resolution": "Check the request resource URI. Refer to
                    the OpenManage Enterprise-Modular User's Guide for more
                    information about resource URI and its properties.",
                    "Severity": "Critical"
                }
            ],
            "code": "Base.1.0.GeneralError",
            "message": "A general error has occurred. See ExtendedInfo for more information."
        }
    }
'''

import json
from ssl import SSLError
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.remote_management.dellemc.ome import RestOME
from ansible.module_utils.urls import open_url, ConnectionError, SSLValidationError
from ansible.module_utils.six.moves.urllib.error import URLError, HTTPError

NETWORK_HIERARCHY_VIEW = 4  # For Network hierarchy View in a Template
UPDATE_NETWORK_CONFIG = "TemplateService/Actions/TemplateService.UpdateNetworkConfig"
TEMPLATE_ATTRIBUTE_VIEW = "TemplateService/Templates({0})/Views({1}" \
                          ")/AttributeViewDetails"
VLAN_NETWORKS = "NetworkConfigurationService/Networks?$top=9999"
TEMPLATE_VIEW = "TemplateService/Templates"

KEY_ATTR_NAME = 'DisplayName'
SUB_GRP_ATTR_NAME = 'SubAttributeGroups'
GRP_ATTR_NAME = 'Attributes'
GRP_NAME_ID_ATTR_NAME = 'GroupNameId'
CUSTOM_ID_ATTR_NAME = 'CustomId'


def get_item_id(rest_obj, name, uri):
    resp = rest_obj.invoke_request('GET', uri)
    if resp.success and resp.json_data.get('value'):
        tlist = resp.json_data.get('value', [])
        for xtype in tlist:
            if xtype.get('Name', "") == name:
                return xtype.get('Id')
    return 0


def get_vlan_name_id_map(rest_obj):
    k = "Name"
    v = "Id"
    d = {}
    resp = rest_obj.invoke_request('GET', VLAN_NETWORKS)
    if resp.success and resp.json_data.get('value'):
        tlist = resp.json_data.get('value', [])
        for xtype in tlist:
            d[xtype[k]] = xtype[v]
    return d


def get_template_vlan_info(module, rest_obj, template_id):
    port_id_map = {}
    port_untagged_map = {}
    port_tagged_map = {}
    resp = rest_obj.invoke_request('GET', TEMPLATE_ATTRIBUTE_VIEW.format(
        template_id, NETWORK_HIERARCHY_VIEW))
    if resp.success:
        nic_id = module.params.get("nic_identifier")
        nic_model = resp.json_data.get('AttributeGroups', [])
        nic_group = nic_model[0]['SubAttributeGroups']
        nic_found = False
        for nic in nic_group:
            if nic_id == nic.get(KEY_ATTR_NAME):
                nic_found = True
                for port in nic.get(SUB_GRP_ATTR_NAME):  # ports
                    for partition in port.get(SUB_GRP_ATTR_NAME):  # partitions
                        for attribute in partition.get(GRP_ATTR_NAME):  # attributes
                            if attribute.get(CUSTOM_ID_ATTR_NAME) != 0:
                                port_number = port.get(GRP_NAME_ID_ATTR_NAME)
                                port_id_map[port_number] = attribute.get(CUSTOM_ID_ATTR_NAME)
                                if attribute.get(KEY_ATTR_NAME).lower() == "vlan untagged":
                                    port_untagged_map[port_number] = int(attribute['Value'])
                                if attribute.get(KEY_ATTR_NAME).lower() == "vlan tagged":
                                    port_tagged_map[port_number] = []
                                    if attribute['Value']:
                                        port_tagged_map[port_number] = \
                                            list(map(int, (attribute['Value']).replace(" ", "").split(",")))
        if not nic_found:
            module.fail_json(msg="NIC with name '{0}' not found for template with id {1}".format(nic_id, template_id))
    return port_id_map, port_untagged_map, port_tagged_map


def compare_nested_dict(modify_setting_payload, existing_setting_payload):
    """compare existing and requested setting values of identity pool in case of modify operations
    if both are same return True"""
    for key, val in modify_setting_payload.items():
        if existing_setting_payload.get(key) is None:
            return False
        elif isinstance(val, dict):
            if not compare_nested_dict(val, existing_setting_payload.get(key)):
                return False
        elif val != existing_setting_payload.get(key):
            return False
    return True


def get_vlan_payload(module, rest_obj, untag_dict, tagged_dict):
    payload = {}
    template_id = module.params.get("template_id")
    if not template_id:
        template_id = get_item_id(rest_obj, module.params.get("template_name"), TEMPLATE_VIEW)
    payload["TemplateId"] = template_id
    # VlanAttributes
    port_id_map, port_untagged_map, port_tagged_map = get_template_vlan_info(module, rest_obj, template_id)
    untag_equal_dict = compare_nested_dict(untag_dict, port_untagged_map)
    tag_equal_dict = compare_nested_dict(tagged_dict, port_tagged_map)
    if untag_equal_dict and tag_equal_dict:
        module.exit_json(msg="No changes found to be applied")
    vlan_attributes = []
    for pk, pv in port_id_map.items():
        mdict = {}
        if pk in untag_dict or pk in tagged_dict:
            mdict["Untagged"] = untag_dict.pop(pk, port_untagged_map.get(pk))
            mdict["Tagged"] = tagged_dict.pop(pk, port_tagged_map.get(pk))
            mdict["ComponentId"] = port_id_map.get(pk)
        if mdict:
            vlan_attributes.append(mdict)
    if untag_dict:
        module.fail_json(msg="Invalid port(s) {0} found for untagged "
                             "vLAN".format(untag_dict.keys()))
    if tagged_dict:
        module.fail_json(msg="Invalid port(s) {0} found for tagged "
                             "vLAN".format(tagged_dict.keys()))
    payload["VlanAttributes"] = vlan_attributes
    return payload


def get_key(val, my_dict):
    for key, value in my_dict.items():
        if val == value:
            return key
    return None


def validate_vlans(module, rest_obj):
    vlan_name_id_map = get_vlan_name_id_map(rest_obj)
    vlan_name_id_map["0"] = 0
    tagged_list = module.params.get("tagged_networks")
    untag_list = module.params.get("untagged_networks")
    if not tagged_list and not untag_list:
        module.fail_json(msg="Either tagged_networks | untagged_networks "
                             "data needs to be provided")
    untag_dict = {}
    if untag_list:
        for utg in untag_list:
            p = utg["port"]
            excl_flag = False
            if utg.get("untagged_network_id") is not None:
                if p in untag_dict:
                    module.fail_json(msg="port {0} is repeated for "
                                         "untagged_network_id".format(p))
                vlan = utg.get("untagged_network_id")
                if vlan not in vlan_name_id_map.values():
                    module.fail_json(msg="untagged_network_id: {0} is not a "
                                         "valid vlan id for port {1}".
                                     format(vlan, p))
                untag_dict[p] = vlan
                excl_flag = True
            if utg.get("untagged_network_name"):
                if excl_flag:
                    module.fail_json(msg="Options untagged_network_name | "
                                         "untagged_network_id are mutually exclusive "
                                         "for port {0}".format(p))
                vlan = utg.get("untagged_network_name")
                if vlan in vlan_name_id_map:
                    if p in untag_dict:
                        module.fail_json(msg="port {0} is repeated for "
                                             "untagged_network_name".format(p))
                    untag_dict[p] = vlan_name_id_map.get(vlan)
                else:
                    module.fail_json(msg="{0} is not a valid vlan name for port {1}".format(vlan, p))
    vlan_name_id_map.pop("0")
    tagged_dict = {}
    if tagged_list:
        for tg in tagged_list:
            p = tg["port"]
            tg_list = []
            empty_list = False
            tgnids = tg.get("tagged_network_ids")
            if isinstance(tgnids, list):
                if len(tgnids) == 0:
                    empty_list = True
                for vl in tgnids:
                    if vl not in vlan_name_id_map.values():
                        module.fail_json(msg="{0} is not a valid vlan id "
                                             "port {1}".format(vl, p))
                    tg_list.append(vl)
            tgnames = tg.get("tagged_network_names")
            if isinstance(tgnames, list):
                if len(tgnames) == 0:
                    empty_list = True
                for vln in tgnames:
                    if vln not in vlan_name_id_map:
                        module.fail_json(msg="{0} is not a valid vlan name "
                                             "port {1}".format(vln, p))
                    tg_list.append(vlan_name_id_map.get(vln))
            if not tg_list and not empty_list:
                module.fail_json(msg="No tagged_networks provided or valid tagged_networks not found for port {0}"
                                 .format(p))
            tagged_dict[p] = list(set(tg_list))  # Will not report duplicates
    for k, v in untag_dict.items():
        if v in tagged_dict.get(k, []):
            module.fail_json(msg="vlan {0}('{1}') cannot be in both tagged and untagged list for port {2}".
                             format(v, get_key(v, vlan_name_id_map), k))
    return untag_dict, tagged_dict


def main():
    port_untagged_spec = {"port": {"required": True, "type": "int"},
                          "untagged_network_id": {"type": "int"},
                          "untagged_network_name": {"type": "str"}}
    port_tagged_spec = {"port": {"required": True, "type": "int"},
                        "tagged_network_ids": {"type": "list", "elements": "int"},
                        "tagged_network_names": {"type": "list", "elements": "str"}}
    module = AnsibleModule(
        argument_spec={
            "hostname": {"required": True, "type": "str"},
            "username": {"required": True, "type": "str"},
            "password": {"required": True, "type": "str", "no_log": True},
            "port": {"required": False, "type": "int", "default": 443},
            "template_name": {"required": False, "type": "str"},
            "template_id": {"required": False, "type": "int"},
            "nic_identifier": {"required": True, "type": "str"},
            "untagged_networks": {"required": False, "type": "list", "elements": "dict", "options": port_untagged_spec},
            "tagged_networks": {"required": False, "type": "list", "elements": "dict", "options": port_tagged_spec}
        },
        required_one_of=[("template_id", "template_name"),
                         ("untagged_networks", "tagged_networks")],
        mutually_exclusive=[("template_id", "template_name"),
                            ("untagged_network_id", "untagged_network_name")],
    )
    try:
        with RestOME(module.params, req_session=True) as rest_obj:
            untag_dict, tagged_dict = validate_vlans(module, rest_obj)
            payload = get_vlan_payload(module, rest_obj, untag_dict, tagged_dict)
            resp = rest_obj.invoke_request("POST", UPDATE_NETWORK_CONFIG, data=payload)
            if resp.success:
                module.exit_json(msg="Successfully applied the network "
                                     "settings to the template", changed=True)
    except HTTPError as err:
        module.fail_json(msg=str(err), error_info=json.load(err))
    except URLError as err:
        module.exit_json(msg=str(err), unreachable=True)
    except (IOError, ValueError, SSLError, TypeError, ConnectionError, SSLValidationError) as err:
        module.fail_json(msg=str(err))
    except Exception as err:
        module.fail_json(msg=str(err))


if __name__ == "__main__":
    main()
