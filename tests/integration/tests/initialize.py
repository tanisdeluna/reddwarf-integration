# Copyright (c) 2011 OpenStack, LLC.
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

import unittest
import os
import time
import socket

from nose.plugins.skip import SkipTest

from proboscis import test
from proboscis.asserts import fail
from proboscis.decorators import time_out
from tests.util.services import Service
from tests.util.services import start_proc
from tests.util.services import WebService
from tests import CONFIG
from tests import WHITE_BOX

if WHITE_BOX:
    from nova import context
    from nova import utils
    from nova.db import api as dbapi

FAKE = CONFIG.fake_mode
START_SERVICES = (not FAKE) and CONFIG.values.get('start_services', False)
KEYSTONE_ALL = CONFIG.values.get('keystone_use_combined', True)

dbaas_image = None
instance_name = None
success_statuses = ["build", "active"]


def dbaas_url():
    return str(CONFIG.values.get("dbaas_url"))

def nova_url():
    return str(CONFIG.values.get("nova_client")['url'])



class Daemon(object):
    """Starts a daemon."""

    def __init__(self, alternate_path=None, conf_file_name=None,
                 extra_cmds=None, service_path_root=None, service_path=None):
        # The path to the daemon bin if the other one doesn't work.
        self.alternate_path = alternate_path
        self.extra_cmds = extra_cmds or []
        # The name of a test config value which points to a conf file.
        self.conf_file_name = conf_file_name
        # The name of a test config value, which is inserted into the service_path.
        self.service_path_root = service_path_root
        # The first path to the daemon bin we try.
        self.service_path = service_path or "%s"

    def run(self):
        # Print out everything to make it
        print("Looking for config value %s..." % self.service_path_root)
        print(CONFIG.values[self.service_path_root])
        path = self.service_path % CONFIG.values[self.service_path_root]
        print("Path = %s" % path)
        if not os.path.exists(path):
            path = self.alternate_path
        if path is None:
            fail("Could not find path to %s" % self.service_path_root)
        conf_path = str(CONFIG.values[self.conf_file_name])
        cmds = CONFIG.python_cmd_list() + [path] + self.extra_cmds + \
               [conf_path]
        print("Running cmds: %s" % cmds)
        self.service = Service(cmds)
        if not self.service.is_service_alive():
            self.service.start()

@test(groups=["services.initialize"],
      enabled=START_SERVICES and (not KEYSTONE_ALL))
def start_keystone_all():
    """Starts the Keystone API."""
    Daemon(service_path_root="keystone_code_root",
           service_path="%s/bin/keystone-all",
           extra_cmds=['--config-file'],
           conf_file_name="keystone_conf").run()


@test(groups=["services.initialize", "services.initialize.glance"],
      enabled=START_SERVICES)
def start_glance_registry():
    """Starts the Glance Registry."""
    Daemon(alternate_path="/usr/bin/glance-registry",
           conf_file_name="glance_reg_conf",
           service_path_root="glance_code_root",
           service_path="%s/bin/glance-registry").run()


@test(groups=["services.initialize", "services.initialize.glance"],
      depends_on=[start_glance_registry], enabled=START_SERVICES)
def start_glance_api():
    """Starts the Glance API."""
    Daemon(alternate_path="/usr/bin/glance-api",
           conf_file_name="glance_reg_conf",
           service_path_root="glance_code_root",
           service_path="%s/bin/glance-api").run()


@test(groups=["services.initialize"], depends_on_classes=[start_glance_api],
      enabled=START_SERVICES)
def start_nova_network():
    """Starts the Nova Network Service."""
    Daemon(service_path_root="nova_code_root",
           service_path="%s/bin/nova-network",
           extra_cmds=['--config-file='],
           conf_file_name="nova_conf").run()


@test(groups=["services.initialize"], enabled=START_SERVICES)
def start_scheduler():
    """Starts the Scheduler Service."""
    Daemon(service_path_root="nova_code_root",
           service_path="%s/bin/nova-scheduler",
           extra_cmds=['--config-file='],
           conf_file_name="nova_conf").run()

@test(groups=["services.initialize"],
      depends_on_classes=[start_glance_api, start_nova_network],
      enabled=START_SERVICES)
def start_compute():
    """Starts the Nova Compute Service."""
    Daemon(service_path_root="nova_code_root",
           service_path="%s/bin/nova-compute",
           extra_cmds=['--config-file='],
           conf_file_name="nova_conf").run()


@test(groups=["services.initialize"], depends_on_classes=[start_scheduler],
      enabled=START_SERVICES)
def start_volume():
    """Starts the Nova Compute Service."""
    Daemon(service_path_root="nova_code_root",
           service_path="%s/bin/nova-volume",
           extra_cmds=['--config-file='],
           conf_file_name="nova_conf").run()


@test(groups=["services.initialize"],
      depends_on_classes=[start_glance_api, start_nova_network, start_compute,
                          start_volume],
      enabled=START_SERVICES)
def start_nova_api():
    """Starts the Nova Compute Service."""
    Daemon(service_path_root="nova_code_root",
           service_path="%s/bin/nova-api",
           extra_cmds=['--config-file='],
           conf_file_name="nova_conf").run()


@test(groups=["services.initialize"],
      depends_on_classes=[start_nova_api],
      enabled=START_SERVICES)
def start_reddwarf_api():
    """Starts the Reddwarf Service."""
    Daemon(service_path_root="reddwarf_code_root",
           service_path="%s/bin/reddwarf-api",
           extra_cmds=['--config-file='],
           conf_file_name="reddwarf_conf").run()
