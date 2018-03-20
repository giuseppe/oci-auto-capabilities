#!/bin/env python
# oci-auto-capabilities.py - find the smallest set of needed capabilities
#
# Copyright (C) 2018 Giuseppe Scrivano <giuseppe@scrivano.org>
# crun is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# crun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with oci-auto-capabilities.py.
# If not, see <http://www.gnu.org/licenses/>.

import python_crun
import json
import concurrent.futures
import sys
import time
import os
import argparse
import copy
import uuid

ALL_CAPS = ['CAP_CHOWN',
            'CAP_DAC_OVERRIDE',
            'CAP_DAC_READ_SEARCH',
            'CAP_FOWNER',
            'CAP_FSETID',
            'CAP_KILL',
            'CAP_SETGID',
            'CAP_SETUID',
            'CAP_SETPCAP',
            'CAP_LINUX_IMMUTABLE',
            'CAP_NET_BIND_SERVICE',
            'CAP_NET_BROADCAST',
            'CAP_NET_ADMIN',
            'CAP_NET_RAW',
            'CAP_IPC_LOCK',
            'CAP_IPC_OWNER',
            'CAP_SYS_MODULE',
            'CAP_SYS_RAWIO',
            'CAP_SYS_CHROOT',
            'CAP_SYS_PTRACE',
            'CAP_SYS_PACCT',
            'CAP_SYS_ADMIN',
            'CAP_SYS_BOOT',
            'CAP_SYS_NICE',
            'CAP_SYS_RESOURCE',
            'CAP_SYS_TIME',
            'CAP_SYS_TTY_CONFIG',
            'CAP_MKNOD',
            'CAP_LEASE',
            'CAP_AUDIT_WRITE',
            'CAP_AUDIT_CONTROL',
            'CAP_SETFCAP',
            'CAP_MAC_OVERRIDE',
            'CAP_MAC_ADMIN',
            'CAP_SYSLOG',
            'CAP_WAKE_ALARM',
            'CAP_BLOCK_SUSPEND',
            'CAP_AUDIT_READ']

TYPES_CAPS = ['bounding', 'effective', 'permitted', 'ambient', 'inheritable']
def run_container(conf):
    name = "test-%s" % uuid.uuid4()
    ctr = python_crun.load_from_memory(json.dumps(conf))
    ctx = python_crun.make_context(name)
    try:
        ret = python_crun.run(ctx, ctr)
        success = ret == 0
    except Exception as e:
        print(e)
        success = False
    return success, conf

def make_new_conf_all_same_caps(conf, caps):
    new_conf = copy.deepcopy(conf)
    new_conf['process']['capabilities'] = {'bounding' : caps, 'effective' : caps,
                                           'permitted' : caps, 'ambient' : caps,
                                           'inheritable' : caps}
    return new_conf

def make_new_conf_change_type(conf, typ, caps):
    new_conf = copy.deepcopy(conf)
    new_conf['process']['capabilities'][typ] = caps
    return new_conf

def intersect(conf, futures):
    for i in TYPES_CAPS:
        conf['process']['capabilities'][i] = set(conf['process']['capabilities'][i])
    for success, future_conf in futures:
        if success:
            for i in TYPES_CAPS:
                conf['process']['capabilities'][i] = conf['process']['capabilities'][i].intersection(future_conf['process']['capabilities'][i])
    for i in TYPES_CAPS:
        conf['process']['capabilities'][i] = list(conf['process']['capabilities'][i])
    return conf

def remove_cap(caps, cap):
    caps = caps[:]
    if cap in caps:
        caps.remove(cap)
    return caps

def start(executor, conf):
    conf['process']['capabilities'] = {}
    for i in TYPES_CAPS:
        conf['process']['capabilities'][i] = ALL_CAPS[:]
    subcaps = [remove_cap(ALL_CAPS, i) for i in ALL_CAPS]
    futures = executor.map(run_container, [make_new_conf_all_same_caps(conf, i) for i in subcaps])
    conf = intersect(conf, futures)

    # No caps needed, return immediately
    if not any([i for i in conf['process']['capabilities'].values() if len(i) > 0]):
        return conf

    for typ in TYPES_CAPS:
        all_type_caps = conf['process']['capabilities'][typ]
        subcaps = [remove_cap(all_type_caps, i) for i in all_type_caps]
        futures = executor.map(run_container, [make_new_conf_change_type(conf, typ, i) for i in subcaps])
        conf = intersect(conf, futures)        
    return conf

if __name__ == '__main__':
    python_crun.set_verbosity(python_crun.VERBOSITY_ERROR)


    parser = argparse.ArgumentParser(description='Find the minimum needed capabilities.')
    parser.add_argument('bundle', metavar='PATH', help='path to the OCI bundle')
    parser.add_argument('--sequential', default=False, dest='sequential', action='store_true', help='run only one instance of the container at a time')
    parser.add_argument('--test', default=None, dest='test', help='test to run inside the container to validate the configuration')
    parser.add_argument('--force', default=False, action='store_true', dest='force', help='overwrite the destination file')

    args = parser.parse_args()

    if args.test is None:
        print("Please specify a test program")
        sys.exit(1)

    dfile = os.path.join(args.bundle, 'config.json.new')
    if not args.force and os.path.exists(dfile):
        print("The file %s already exists" % dfile)
        sys.exit(1)
        
    os.chdir(args.bundle)

    with open(os.path.join(args.bundle, 'config.json')) as f:
        orig_conf = json.load(f)
        conf = copy.deepcopy(orig_conf)
    conf['root']['path'] = os.path.realpath(os.path.join(args.bundle, conf['root']['path']))
    src = os.path.realpath(os.path.join(os.getcwd(), args.test))
    conf['mounts'] = conf['mounts'] + [{'type' : 'bind', 'source' : src, 'destination' : '/usr/bin/test-script',
                                       'options': ['nosuid', 'nodev', 'mode=777']}]
    conf['process']['args'] = ['/usr/bin/test-script']
    max_workers = 1 if args.sequential else 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        conf = start(executor, copy.deepcopy(conf))
    print(conf['process']['capabilities'])
    with open(dfile, "w+") as f:
        orig_conf['process']['capabilities'] = conf['process']['capabilities']
        f.write(json.dumps(orig_conf, indent=4))
        print("Written %s\n" % dfile)
    
