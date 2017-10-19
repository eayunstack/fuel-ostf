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


class CeilometerApiSmokeTests(ceilometermanager.CeilometerBaseTest):
    """
    TestClass contains tests that check basic Ceilometer functionality.
    """

    def test_create_alarm(self):
        """Ceilometer create, update, check, delete alarm
        Target component: Ceilometer

        Scenario:
            1. Create a new instance.
            2. Instance become active.
            3. Create a new alarm.
            4. List alarms
            5. Wait for 'ok' alarm state.
            6. Update the alarm.
            7. Wait for 'alarm' alarm state.
            8. Get alarm history.
            9. Update the alarm.
            10. Change alarm state to 'ok'.
            11. Verify state.
            12. Delete the alarm.
            13. Delete instance.
        Duration: 2300 s.
        Deployment tags: Ceilometer
        """

        # TODO(vrovachev): refactor this test suite after resolve bug:
        # https://bugs.launchpad.net/fuel/+bug/1314196

        self.check_image_exists()

        name = rand_name('ost1-test-ceilo-instance-')

        fail_msg = "Creation instance is failed."
        msg = "Instance was created."

        self.instance = self.verify(600, self._create_server, 1,
                                    fail_msg, msg,
                                    self.compute_client, name)

        fail_msg = "Instance is not available."
        msg = "instance becoming available."

        self.verify(200, self.wait_for_instance_status, 2,
                    fail_msg, msg,
                    self.instance, 'ACTIVE')

        fail_msg = "Creation of alarm is failed."
        msg = "Creation of alarm is successful."

        alarm = self.verify(60, self.create_alarm, 3,
                            fail_msg, msg,
                            meter_name='cpu_util',
                            threshold=80,
                            name=rand_name('ceilometer-alarm'),
                            comparison_operator='ge')

        fail_msg = 'Getting alarms is failed.'
        msg = 'Getting alarms is successful.'
        query = [{'field': 'project', 'op': 'eq', 'value': alarm.project_id}]

        self.verify(60, self.ceilometer_client.alarms.list, 4,
                    fail_msg, msg, q=query)

        fail_msg = "Alarm status is not equal 'ok'."
        msg = "Alarm status is 'ok'."

        self.verify(1000, self.wait_for_alarm_status, 5,
                    fail_msg, msg,
                    alarm.alarm_id, 'ok')

        fail_msg = "Alarm update failed."
        msg = "Alarm was updated."

        self.verify(60, self.ceilometer_client.alarms.update, 6,
                    fail_msg, msg,
                    alarm_id=alarm.alarm_id,
                    threshold=0)

        fail_msg = "Alarm verify state is failed."
        msg = "Alarm status is 'alarm'."

        self.verify(1000, self.wait_for_alarm_status, 7,
                    fail_msg, msg,
                    alarm.alarm_id, 'alarm')

        fail_msg = "Getting history of alarm is failed."
        msg = 'Getting alarms history is successful.'

        self.verify(60, self.ceilometer_client.alarms.get_history, 8,
                    fail_msg, msg,
                    alarm_id=alarm.alarm_id)

        fail_msg = "Alarm update failed."
        msg = "Alarm was updated."

        self.verify(60, self.ceilometer_client.alarms.update, 9,
                    fail_msg, msg,
                    alarm_id=alarm.alarm_id,
                    threshold=0)

        fail_msg = "Setting alarm state to 'insufficient data' is failed."
        msg = "Set alarm state to 'insufficient data'."

        self.verify(60, self.ceilometer_client.alarms.set_state, 10,
                    fail_msg, msg,
                    alarm_id=alarm.alarm_id,
                    state='insufficient data')

        fail_msg = "Alarm state verification is failed."
        msg = "Alarm state verification is successful."

        self.verify(60, self.verify_state, 11,
                    fail_msg, msg,
                    alarm_id=alarm.alarm_id,
                    state='insufficient data')

        fail_msg = "Alarm deleting is failed."
        msg = "Alarm deleted."

        self.verify(60, self.ceilometer_client.alarms.delete, 12,
                    fail_msg, msg,
                    alarm_id=alarm.alarm_id)

        fail_msg = "Server can not be deleted."
        msg = "Server deletion."

        self.verify(30, self._delete_server, 13,
                    fail_msg, msg,
                    self.instance.id)
