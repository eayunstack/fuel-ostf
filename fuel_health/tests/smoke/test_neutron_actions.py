# Copyright 2014 Mirantis, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging

from fuel_health.common.utils.data_utils import rand_name
from fuel_health import neutronmanager

LOG = logging.getLogger(__name__)


class TestNeutron(neutronmanager.NeutronBaseTest):
    """
    Test suite verifies:
    - router creation
    - network creation
    - subnet creation
    - opportunity to attach network to router
    - instance creation in created network
    - instance network connectivity
    """

    def test_check_neutron_objects_creation(self):
        """Check network connectivity from instance via floating IP
        Target component: Neutron

        Scenario:
            1. Create a new security group (if it doesn`t exist yet).
            2. Create router
            3. Create router2
            4. Create network
            5. Create subnet
            6. Uplink subnet to router.
            7. Create an instance using the new security group
               in created subnet.
            8. Create a new floating IP
            9. Assign the new floating IP to the instance.
            10. Update router2.
            11. Get router2 hosting agent.
            12. Check connectivity to the floating IP using ping command.
            13. Disassociate server floating ip.
            14. Delete floating ip
            15. Delete server.
            16. Remove router.
            17. Remove router2.
            18. Remove subnet
            19. Remove network

        Duration: 390 s.

        Deployment tags: neutron
        """

        self.check_image_exists()
        if not self.security_groups:
            self.security_groups[self.tenant_id] = self.verify(
                25, self._create_security_group, 1,
                "Security group can not be created.",
                'security group creation',
                self.compute_client)

        name = rand_name('ost1_test-server-smoke-')
        security_groups = [self.security_groups[self.tenant_id].name]

        router = self.verify(30, self.create_router, 2,
                             'Router can not be created', 'Router creation',
                             name)

        router2_name = rand_name('ost1_test-server-smoke-')
        router2 = self.verify(30, self.create_router, 3,
                              'Router(router2) can not be created',
                              'Router(router2) creation',
                              router2_name)

        network = self.verify(20, self.create_network, 4,
                              'Network can not be created',
                              'Network creation', name)

        subnet = self.verify(20, self.create_subnet, 5,
                             'Subnet can not be created',
                             'Subnet creation', network)

        self.verify(20, self.uplink_subnet_to_router, 6,
                    'Can not uplink subnet to router',
                    'Uplink subnet to router', router, subnet)

        server = self.verify(200, self._create_server, 7,
                             "Server can not be created.",
                             "server creation",
                             self.compute_client, name, security_groups,
                             net_id=network['id'])

        floating_ip = self.verify(
            20,
            self._create_floating_ip,
            8,
            "Floating IP can not be created.",
            'floating IP creation')

        self.verify(10, self._assign_floating_ip_to_instance,
                    9, "Floating IP can not be assigned.",
                    'floating IP assignment',
                    self.compute_client, server, floating_ip)

        self.floating_ips.append(floating_ip)

        ip_address = floating_ip.ip
        LOG.info('is address is  {0}'.format(ip_address))
        LOG.debug(ip_address)

        # TODO(blkart): remove this stage after resolve bug:
        # https://bugs.launchpad.net/horizon/+bug/1535707
        fail_msg = "Update router %s failed." % router2['id']
        msg = "Update router %s successfully." % router2['id']
        self.verify(30, self._update_router, 10, fail_msg, msg, router2)

        fail_msg = "Can not get router %s hosting agent." % router2['id']
        msg = "Get router %s hosting agent." % router2['id']
        self.router_host = self.verify(30, self._get_router_host, 11,
                                       fail_msg, msg, router2)

        self.verify(400, self._check_vm_connectivity, 12,
                    "VM connectivity doesn`t function properly.",
                    'VM connectivity checking', ip_address,
                    30, (6, 60), router2['id'])

        self.verify(10, self.compute_client.servers.remove_floating_ip,
                    13, "Floating IP cannot be removed.",
                    "removing floating IP", server, floating_ip)

        self.verify(10, self.compute_client.floating_ips.delete,
                    14, "Floating IP cannot be deleted.",
                    "floating IP deletion", floating_ip)

        if self.floating_ips:
            self.floating_ips.remove(floating_ip)

        self.verify(30, self._delete_server, 15,
                    "Server can not be deleted. ",
                    "server deletion", server)

        self.verify(40, self._remove_router, 16, "Router can not be deleted",
                    "router deletion", router, [subnet['id']])
        self.verify(40, self._remove_router, 17, "Router can not be deleted",
                    "router deletion", router2)
        self.verify(20, self._remove_subnet, 18, "Subnet can not be deleted",
                    "Subnet deletion", subnet)
        self.verify(20, self._remove_network, 19,
                    "Network can not be deleted", "Network deletion", network)
