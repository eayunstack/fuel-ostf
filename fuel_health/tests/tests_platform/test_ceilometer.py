# Copyright 2013 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from fuel_health import ceilometermanager
from fuel_health.common.utils.data_utils import rand_name


class CeilometerApiPlatformTests(ceilometermanager.CeilometerBaseTest):
    """TestClass contains tests that check basic Ceilometer functionality."""

    def test_create_update_delete_alarm(self):
        """Ceilometer test to create, update, check and delete alarm
        Target component: Ceilometer

        Scenario:
            1. Get the statistic of a metric.
            2. Create an alarm.
            3. Get the alarm.
            4. List alarms.
            5. Wait for 'ok' alarm state.
            6. Update the alarm.
            7. Wait for 'alarm' alarm state.
            8. Get the alarm history.
            9. Set the alarm state to 'insufficient data'.
            10. Verify that the alarm state is 'insufficient data'.
            11. Delete the alarm.

        Duration: 120 s.
        Deployment tags: Ceilometer
        """

        fail_msg = 'Failed to get statistic of metric.'
        msg = 'getting statistic of metric'
        self.verify(600, self.wait_for_statistic_of_metric, 1,
                    fail_msg, msg, meter_name='image')

        fail_msg = 'Failed to create alarm.'
        msg = 'creating alarm'
        alarm = self.verify(60, self.create_alarm, 2,
                            fail_msg, msg,
                            meter_name='image',
                            threshold=0.9,
                            name=rand_name('ceilometer-alarm'),
                            period=600,
                            statistic='avg',
                            comparison_operator='lt')

        fail_msg = 'Failed to get alarm.'
        msg = 'getting alarm'
        self.verify(60, self.ceilometer_client.alarms.get, 3,
                    fail_msg, msg, alarm.alarm_id)

        fail_msg = 'Failed to list alarms.'
        msg = 'listing alarms'
        query = [{'field': 'project', 'op': 'eq', 'value': alarm.project_id}]
        self.verify(60, self.ceilometer_client.alarms.list, 4,
                    fail_msg, msg, q=query)

        fail_msg = 'Failed while waiting for alarm state to become "ok".'
        msg = 'waiting for alarm state to become "ok"'
        self.verify(1000, self.wait_for_alarm_status, 5,
                    fail_msg, msg, alarm.alarm_id, 'ok')

        fail_msg = 'Failed to update alarm.'
        msg = 'updating alarm'
        self.verify(60, self.ceilometer_client.alarms.update, 6,
                    fail_msg, msg, alarm_id=alarm.alarm_id, threshold=1.1)

        fail_msg = 'Failed while waiting for alarm state to become "alarm".'
        msg = 'waiting for alarm state to become "alarm"'
        self.verify(1000, self.wait_for_alarm_status, 7,
                    fail_msg, msg, alarm.alarm_id, 'alarm')

        fail_msg = 'Failed to get alarm history.'
        msg = 'getting alarm history'
        self.verify(60, self.ceilometer_client.alarms.get_history, 8,
                    fail_msg, msg, alarm_id=alarm.alarm_id)

        fail_msg = 'Failed to set alarm state to "insufficient data".'
        msg = 'setting alarm state to "insufficient data"'
        self.verify(60, self.ceilometer_client.alarms.set_state, 9,
                    fail_msg, msg, alarm_id=alarm.alarm_id,
                    state='insufficient data')

        fail_msg = 'Failed while verifying alarm state.'
        msg = 'verifying alarm state'
        self.verify(60, self.verify_state, 10,
                    fail_msg, msg, alarm_id=alarm.alarm_id,
                    state='insufficient data')

        fail_msg = 'Failed to delete alarm.'
        msg = 'deleting alarm'
        self.verify(60, self.ceilometer_client.alarms.delete, 11,
                    fail_msg, msg, alarm_id=alarm.alarm_id)

    @ceilometermanager.check_compute_nodes()
    def test_check_alarm_state(self):
        """Ceilometer test to check alarm state and get Nova metrics
        Target component: Ceilometer

        Scenario:
            1. Create an instance.
            2. Wait for 'ACTIVE' status of the instance.
            3. Get notifications.
            4. Get instance pollsters.
            5. Get disk pollsters.
            6. Get the statistic notification:cpu_util.
            7. Create an alarm for the summary statistic notification:cpu_util.
            8. Wait for the alarm state to become 'alarm' or 'ok'.

        Duration: 150 s.
        Deployment tags: Ceilometer
        """

        self.check_image_exists()
        private_net_id, _ = self.create_network_resources()

        fail_msg = 'Failed to create instance.'
        msg = 'creating instance'
        name = rand_name('ostf-ceilo-instance-')
        vcenter = self.config.compute.use_vcenter
        image_name = 'TestVM-VMDK' if vcenter else None
        instance = self.verify(600, self.create_server, 1, fail_msg, msg, name,
                               net_id=private_net_id, img_name=image_name)

        fail_msg = 'Failed while waiting for "ACTIVE" status of instance.'
        msg = 'waiting for "ACTIVE" status of instance'
        self.verify(200, self.wait_for_resource_status, 2,
                    fail_msg, msg, self.compute_client.servers,
                    instance.id, 'ACTIVE')

        fail_msg = 'Failed to get notifications.'
        msg = 'getting notifications'
        notifications = self.nova_notifications if not vcenter else []
        query = [{'field': 'resource', 'op': 'eq', 'value': instance.id}]
        self.verify(600, self.wait_metrics, 3,
                    fail_msg, msg, notifications, query)

        instance_pollsters = (self.nova_instance_pollsters if not vcenter
                              else self.nova_vsphere_pollsters)
        instance_pollsters.append("".join(['instance:',
                                           self.compute_client.flavors.get(
                                               instance.flavor['id']).name]))
        fail_msg = 'Failed to get instance pollsters.'
        msg = 'getting instance pollsters'
        self.verify(600, self.wait_metrics, 4, fail_msg, msg,
                    instance_pollsters, query)

        fail_msg = 'Failed to get disk.device.* pollsters.'
        msg = 'getting disk.device.* pollsters'
        query_disk_device_pollsters = [{'field': 'resource', 'op': 'eq',
                                        'value': "".join(
                                            [instance.id, '-vda'])}]

        disk_device_pollsters = (self.nova_disk_device_pollsters if not vcenter
                                 else [])

        self.verify(600, self.wait_metrics, 5,
                    fail_msg, msg, disk_device_pollsters,
                    query_disk_device_pollsters)

        fail_msg = 'Failed to get statistic notification:cpu_util.'
        msg = 'getting statistic notification:cpu_util'
        cpu_util_stat = self.verify(60, self.wait_for_statistic_of_metric, 6,
                                    fail_msg, msg, 'cpu_util', query)

        fail_msg = ('Failed to create alarm for '
                    'summary statistic notification:cpu_util.')
        msg = 'creating alarm for summary statistic notification:cpu_util'
        threshold = cpu_util_stat[0].sum - 1
        alarm = self.verify(60, self.create_alarm, 7,
                            fail_msg, msg,
                            meter_name='cpu_util',
                            threshold=threshold,
                            name=rand_name('ceilometer-alarm'),
                            period=600,
                            statistic='sum',
                            comparison_operator='lt')

        fail_msg = ('Failed while waiting for '
                    'alarm state to become "alarm" or "ok".')
        msg = 'waiting for alarm state to become "alarm" or "ok"'
        self.verify(1000, self.wait_for_alarm_status, 8,
                    fail_msg, msg, alarm.alarm_id)

    def test_create_sample(self):
        """Ceilometer test to create, check and list samples
        Target component: Ceilometer

        Scenario:
            1. Request the list of samples for an image.
            2. Create a sample for the image.
            3. Check that the sample has the expected resource.
            4. Get samples and compare samples lists before and after
               the sample creation.
            5. Get the resource of the sample.

        Duration: 5 s.
        Deployment tags: Ceilometer
        """

        self.check_image_exists()

        image_id = self.get_image_from_name()
        query = [{'field': 'resource', 'op': 'eq', 'value': image_id}]
        fail_msg = 'Failed to get samples for image.'
        msg = 'getting samples for image'
        list_before_create_sample = self.verify(
            60, self.ceilometer_client.samples.list, 1,
            fail_msg, msg, self.glance_notifications[0], q=query)

        fail_msg = 'Failed to create sample for image.'
        msg = 'creating sample for image'
        sample = self.verify(60, self.ceilometer_client.samples.create, 2,
                             fail_msg, msg,
                             resource_id=image_id,
                             counter_name=self.glance_notifications[0],
                             counter_type='delta',
                             counter_unit='image',
                             counter_volume=1,
                             resource_metadata={'user': 'example_metadata'})

        fail_msg = ('Resource of sample is missing or '
                    'does not equal to the expected resource.')
        self.verify_response_body_value(body_structure=sample[0].resource_id,
                                        value=image_id,
                                        msg=fail_msg,
                                        failed_step=3)

        fail_msg = ('Failed while waiting '
                    'for addition of new sample to samples list.')
        msg = 'waiting for addition of new sample to samples list'
        self.verify(20, self.wait_samples_count, 4,
                    fail_msg, msg, self.glance_notifications[0],
                    query, len(list_before_create_sample))

        fail_msg = 'Failed to get resource of sample.'
        msg = 'getting resource of sample'
        self.verify(20, self.ceilometer_client.resources.get, 5,
                    fail_msg, msg, sample[0].resource_id)

    @ceilometermanager.check_compute_nodes()
    def test_check_events_and_traits(self):
        """Ceilometer test to check events and traits
        Target component: Ceilometer

        Scenario:
            1. Create an instance.
            2. Wait for 'ACTIVE' status of the instance.
            3. Check that event type list contains expected event type.
            4. Check that event list contains event with expected type.
            5. Check event traits description.
            6. Check that event exists for expected instance.
            7. Get information about expected event.
            8. Get list of all traits for expected event type and trait name.
            9. Delete the instance.

        Duration: 40 s.

        Deployment tags: Ceilometer
        """

        event_type = 'compute.instance.update'

        self.check_image_exists()
        private_net_id, _ = self.create_network_resources()

        name = rand_name('ost1_test-ceilo-instance-')

        fail_msg = 'Failed to create instance.'
        msg = 'creating instance'

        vcenter = self.config.compute.use_vcenter
        image_name = 'TestVM-VMDK' if vcenter else None
        instance = self.verify(600, self.create_server, 1, fail_msg, msg, name,
                               net_id=private_net_id, img_name=image_name)

        fail_msg = 'Failed while waiting for "ACTIVE" status of instance.'
        msg = 'waiting for "ACTIVE" status of instance'
        self.verify(200, self.wait_for_resource_status, 2,
                    fail_msg, msg, self.compute_client.servers,
                    instance.id, 'ACTIVE')

        fail_msg = ('Failed to find "{event_type}" in event type list.'.format(
            event_type=event_type))
        msg = ('searching "{event_type}" in event type list'.format(
            event_type=event_type))
        self.verify(60, self.check_event_type, 3,
                    fail_msg, msg, event_type)

        fail_msg = ('Failed to find event with "{event_type}" type in event '
                    'list.'.format(event_type=event_type))
        msg = ('searching event with "{event_type}" type in event type '
               'list'.format(event_type=event_type))
        query = [{'field': 'event_type', 'op': 'eq', 'value': event_type}]
        events_list = self.verify(60, self.ceilometer_client.events.list, 4,
                                  fail_msg, msg, query)

        if not events_list:
            self.fail('Events with "{event_type}" type not found'.format(
                event_type=event_type))

        traits = ['instance_id', 'request_id', 'state', 'service', 'host']

        fail_msg = 'Failed to check event traits description.'
        msg = 'checking event traits description'
        self.verify(60, self.check_traits, 5, fail_msg, msg,
                    event_type=event_type, traits=traits)

        fail_msg = ('Failed to find "{event_type}" event type with expected '
                    'instance ID.'.format(event_type=event_type))
        msg = ('searching "{event_type}" event type with expected '
               'instance ID'.format(event_type=event_type))
        message_id = self.verify(60, self.check_event_message_id, 6,
                                 fail_msg, msg, events_list, instance.id)

        fail_msg = 'Failed to get event information.'
        msg = 'getting event information'
        self.verify(60, self.ceilometer_client.events.get, 7,
                    fail_msg, msg, message_id)

        fail_msg = ('Failed to get list of all traits for "{event_type}" '
                    'event type and "{trait_name}" trait name.'.format(
                        event_type=event_type, trait_name=traits[0]))
        msg = ('getting list of all traits for "{event_type}" event type and '
               '"{trait_name}" trait name'.format(event_type=event_type,
                                                  trait_name=traits[0]))
        self.verify(60, self.ceilometer_client.traits.list, 8, fail_msg, msg,
                    event_type, traits[0])

        fail_msg = 'Failed to delete the instance.'
        msg = 'instance deleting'
        self.verify(60, self._delete_server, 9, fail_msg, msg, instance)

    @ceilometermanager.check_compute_nodes()
    def test_check_volume_notifications(self):
        """Ceilometer test to check notifications from Cinder
        Target component: Ceilometer

        Scenario:
            1. Create an instance.
            2. Wait for 'ACTIVE' status of the instance.
            3. Create a volume and volume snapshot.
            4. Get volume snapshot notifications.
            5. Get volume notifications.
            6. Delete the instance.

        Duration: 150 s.
        Deployment tags: Ceilometer
        """

        if (not self.config.volume.cinder_node_exist
                and not self.config.volume.ceph_exist):
            self.skipTest('There are no storage nodes for volumes.')

        self.check_image_exists()
        private_net_id, _ = self.create_network_resources()

        fail_msg = 'Failed to create instance.'
        msg = 'creating instance'
        name = rand_name('ostf-ceilo-instance-')
        vcenter = self.config.compute.use_vcenter
        image_name = 'TestVM-VMDK' if vcenter else None
        instance = self.verify(300, self.create_server, 1, fail_msg, msg, name,
                               net_id=private_net_id, img_name=image_name)

        fail_msg = 'Failed while waiting for "ACTIVE" status of instance.'
        msg = 'waiting for "ACTIVE" status of instance'
        self.verify(200, self.wait_for_resource_status, 2,
                    fail_msg, msg, self.compute_client.servers,
                    instance.id, 'ACTIVE')

        fail_msg = 'Failed to create volume and volume snapshot.'
        msg = 'creating volume and volume snapshot'
        volume, snapshot = self.verify(300, self.volume_helper, 3,
                                       fail_msg, msg, instance)

        query = [{'field': 'resource', 'op': 'eq', 'value': snapshot.id}]
        fail_msg = 'Failed to get volume snapshot notifications.'
        msg = 'getting volume snapshot notifications'
        self.verify(300, self.wait_metrics, 4,
                    fail_msg, msg,
                    self.snapshot_notifications, query)

        query = [{'field': 'resource', 'op': 'eq', 'value': volume.id}]
        fail_msg = 'Failed to get volume notifications.'
        msg = 'getting volume notifications'
        self.verify(300, self.wait_metrics, 5,
                    fail_msg, msg, self.volume_notifications, query)

        fail_msg = 'Failed to delete the server.'
        msg = 'deleting server'
        self.verify(30, self._delete_server, 6, fail_msg, msg, instance)

    def test_check_glance_notifications(self):
        """Ceilometer test to check notifications from Glance
        Target component: Ceilometer

        Scenario:
            1. Create an image.
            2. Get image notifications.

        Duration: 5 s.
        Deployment tags: Ceilometer
        """

        fail_msg = 'Failed to create image.'
        msg = 'creating image'
        image = self.verify(120, self.glance_helper, 1, fail_msg, msg)

        query = [{'field': 'resource', 'op': 'eq', 'value': image.id}]
        fail_msg = 'Failed to get image notifications.'
        msg = 'getting image notifications'
        self.verify(600, self.wait_metrics, 2,
                    fail_msg, msg, self.glance_notifications, query)

    def test_check_keystone_notifications(self):
        """Ceilometer test to check notifications from Keystone
        Target component: Ceilometer

        Scenario:
            1. Create Keystone resources.
            2. Get project notifications.
            3. Get user notifications.
            4. Get role notifications.
            5. Get group notifications.
            6. Get trust notifications.

        Duration: 5 s.
        Available since release: 2014.2-6.0
        Deployment tags: Ceilometer
        """

        fail_msg = 'Failed to create some Keystone resources.'
        msg = 'creating Keystone resources'
        tenant, user, role, group, trust = self.verify(60,
                                                       self.identity_helper, 1,
                                                       fail_msg, msg)

        fail_msg = 'Failed to get project notifications.'
        msg = 'getting project notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': tenant.id}]
        self.verify(600, self.wait_metrics, 2, fail_msg, msg,
                    self.keystone_project_notifications, query)

        fail_msg = 'Failed to get user notifications.'
        msg = 'getting user notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': user.id}]
        self.verify(600, self.wait_metrics, 3, fail_msg, msg,
                    self.keystone_user_notifications, query)

        fail_msg = 'Failed to get role notifications.'
        msg = 'getting role notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': role.id}]
        self.verify(600, self.wait_metrics, 4, fail_msg, msg,
                    self.keystone_role_notifications, query)

        fail_msg = 'Failed to get group notifications.'
        msg = 'getting group notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': group.id}]
        self.verify(600, self.wait_metrics, 5, fail_msg, msg,
                    self.keystone_group_notifications, query)

        fail_msg = 'Failed to get trust notifications.'
        msg = 'getting trust notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': trust.id}]
        self.verify(600, self.wait_metrics, 6, fail_msg, msg,
                    self.keystone_trust_notifications, query)

    def test_check_neutron_notifications(self):
        """Ceilometer test to check notifications from Neutron
        Target component: Ceilometer

        Scenario:
            1. Create Neutron resources.
            2. Get network notifications.
            3. Get subnet notifications.
            4. Get port notifications.
            5. Get router notifications.
            6. Get floating IP notifications.

        Duration: 40 s.
        Deployment tags: Ceilometer, Neutron
        """

        fail_msg = 'Failed to create some Neutron resources.'
        msg = 'creating Neutron resources'
        net, subnet, port, router, flip = self.verify(60, self.neutron_helper,
                                                      1, fail_msg, msg)

        fail_msg = 'Failed to get network notifications.'
        msg = 'getting network notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': net['id']}]
        self.verify(60, self.wait_metrics, 2, fail_msg, msg,
                    self.neutron_network_notifications, query)

        fail_msg = 'Failed to get subnet notifications.'
        msg = 'getting subnet notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': subnet['id']}]
        self.verify(60, self.wait_metrics, 3, fail_msg, msg,
                    self.neutron_subnet_notifications, query)

        fail_msg = 'Failed to get port notifications.'
        msg = 'getting port notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': port['id']}]
        self.verify(60, self.wait_metrics, 4, fail_msg, msg,
                    self.neutron_port_notifications, query)

        fail_msg = 'Failed to get router notifications.'
        msg = 'getting router notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': router['id']}]
        self.verify(60, self.wait_metrics, 5, fail_msg, msg,
                    self.neutron_router_notifications, query)

        fail_msg = 'Failed to get floating IP notifications.'
        msg = 'getting floating IP notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': flip['id']}]
        self.verify(60, self.wait_metrics, 6, fail_msg, msg,
                    self.neutron_floatingip_notifications, query)

    @ceilometermanager.check_compute_nodes()
    def test_check_sahara_notifications(self):
        """Ceilometer test to check notifications from Sahara
        Target component: Ceilometer

        Scenario:
            1. Find a correctly registered Sahara image
            2. Create a Sahara cluster
            3. Get cluster notifications

        Duration: 40 s.
        Deployment tags: Ceilometer, Sahara
        """

        plugin_name = 'vanilla'
        hadoop_version = '2.6.0'

        fail_msg = 'Failed to find correctly registered Sahara image.'
        msg = 'finding correctly registered Sahara image'
        image_id = self.verify(60, self.find_and_check_image, 1,
                               fail_msg, msg, plugin_name, hadoop_version)

        if image_id is None:
            self.skipTest('Correctly registered image '
                          'to create Sahara cluster not found.')

        fail_msg = 'Failed to create Sahara cluster.'
        msg = 'creating Sahara cluster'
        cluster = self.verify(300, self.sahara_helper, 2, fail_msg,
                              msg, image_id, plugin_name, hadoop_version)

        fail_msg = 'Failed to get cluster notifications.'
        msg = 'getting cluster notifications'
        query = [{'field': 'resource', 'op': 'eq', 'value': cluster.id}]
        self.verify(60, self.wait_metrics, 3, fail_msg, msg,
                    self.sahara_cluster_notifications, query)
