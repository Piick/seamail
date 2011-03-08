#!/usr/bin/env python
# encoding: utf-8
"""
fabfile.py

Copyright (c) 2011 Piick.com, Inc. All rights reserved.
"""

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of Piick, Inc nor the names of its contributors may be used
# to endorse or promote products derived from this software without specific
# prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


from __future__ import with_statement

from boto.sqs.jsonmessage import JSONMessage as _JSONMessage 
from fabric.api import put, run, local, sudo, require, env
from fabric.decorators import wraps as _wraps
import boto
import logging
import random
import socket
import subprocess
import time


AMI = {
    '10.10': {
        32: {'ebs': 'ami-ccf405a5', 'ec2': 'ami-a6f504cf'},
        64: {'ebs': 'ami-cef405a7', 'ec2': 'ami-08f40561'}
    },
}
ZONES     = ['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d']
VERSION = '0.1'


logging.basicConfig(level=logging.INFO)


require('aws_access_key', 'aws_secret_key', 'key_filename')
ec2 = boto.connect_ec2(env.aws_access_key, env.aws_secret_key)


def _seamail_hosts(func):
    def _get_seamail_hosts():
        rsvps = ec2.get_all_instances()
        lst = []
        for rsvp in rsvps:
          for inst in rsvp.instances:
            if inst.state == 'running' and 'Seamail' in inst.tags:
              lst.append(inst.public_dns_name)
        return lst

    @_wraps(func)
    def _inner_decorator(*args, **kwargs):
        return func(*args, **kwargs)

    _inner_decorator.hosts = list(_get_seamail_hosts())

    return _inner_decorator


def bulk_facebook_send(template, file):
    conn = boto.connect_sqs(env.aws_access_key, env.aws_secret_key)
    q = conn.create_queue('seamail')
    q.set_message_class(_JSONMessage)

    for line in open(file, 'r'):
        id, email, name, first_name, last_name, gender, locale = line.split(',')
        args = {'first_name': first_name, 'last_name': last_name, 
                'gender': gender}
        q.write(_JSONMessage(body=[template, name, email, args, 0]))


def send_message(template, name, email, **kwargs):
    conn = boto.connect_sqs(env.aws_access_key, env.aws_secret_key)
    q = conn.create_queue('seamail')
    q.set_message_class(_JSONMessage)
    q.write(_JSONMessage(body=[template, name, email, kwargs, 0]))


def clear_queue():
    conn = boto.connect_sqs(env.aws_access_key, env.aws_secret_key)
    q = conn.create_queue('seamail')
    q.clear()


def count_queue():
    conn = boto.connect_sqs(env.aws_access_key, env.aws_secret_key)
    q = conn.create_queue('seamail')
    print q.count()


def verify_email(email):
    conn = boto.connect_ses(env.aws_access_key, env.aws_secret_key)
    conn.verify_email_address(email)


def unverify_email(email):
    conn = boto.connect_ses(env.aws_access_key, env.aws_secret_key)
    conn.delete_verified_email_address(email)


def stats():
    conn = boto.connect_ses(env.aws_access_key, env.aws_secret_key)

    print "Verified Addresses"
    print
    emails = conn.list_verified_email_addresses()
    emails = emails['ListVerifiedEmailAddressesResponse']
    emails = emails['ListVerifiedEmailAddressesResult']
    emails = emails['VerifiedEmailAddresses']
    for email in emails:
        print '\t' + email
    print
    print
    
    quotas = conn.get_send_quota()
    quotas = quotas['GetSendQuotaResponse']
    quotas = quotas['GetSendQuotaResult']
    print 'Send Quotas'
    print
    for quota in quotas.iteritems():
        print "\t%s:  %s" % quota
    print
    print
    
    stats = conn.get_send_statistics()
    stats = stats['GetSendStatisticsResponse']
    stats = stats['GetSendStatisticsResult']
    stats = stats['SendDataPoints']
    print 'Send Stats (Deliveries, Bounces, Rejects, Complaints)'
    print
    stats.sort(key=lambda x: x['Timestamp'])
    delivery = bounces = rejects = complaints = 0
    for stat in stats:
        print '\t%s %8d %8d %8d %8d' % \
            (stat['Timestamp'].replace('T', ' '), int(stat['DeliveryAttempts']), 
             int(stat['Bounces']), int(stat['Rejects']), 
             int(stat['Complaints']))
        delivery += int(stat['DeliveryAttempts'])
        bounces += int(stat['Bounces'])
        rejects += int(stat['Rejects'])
        complaints += int(stat['Complaints'])
    print
    print '\tTotals\t\t     %8d %8d %8d %8d' % \
        (delivery, bounces, rejects, complaints)
    print


@_seamail_hosts
def configure(arch=None):
    sudo('apt-get update')
    sudo('export DEBIAN_FRONTEND=noninteractive')
    sudo('apt-get upgrade -y')

    sudo('mkdir -p /opt/seamail/templates')
    sudo('chmod g+w,o+w -R /opt/seamail')
    put('*.py', '/opt/seamail')
    put('seamail.py', '/opt/seamail', mode=0755)
    put('templates/*', '/opt/seamail/templates')
    sudo('chmod g-w,o-w -R /opt/seamail')

    sudo('mkdir -p /etc/supervisor/conf.d')
    put('seamail.conf', '/tmp')
    sudo('mv /tmp/seamail.conf /etc/supervisor/conf.d/')

    sudo('apt-get install -y python-pip supervisor')
    sudo('pip install boto==2.0b4')
    sudo('pip install tornado==1.1.1')
    sudo('pip install fabric==0.9.3')

    if arch:
        pass

    sudo('supervisorctl restart all')


def terminate_cluster():
    rsvps = ec2.get_all_instances()
    lst = []
    for rsvp in rsvps:
      for inst in rsvp.instances:
        if inst.state == 'running' and 'Seamail' in inst.tags:
            print 'Terminating %s' % inst.tags['Name']
            inst.terminate()


def start_nodes(sender_count, key, ec2_type=None):
    _start_instances(sender_count, key, 'seamail', ec2_type)


def _start_instances(instance_count, key, security_groups="", ec2_type=None, 
                    ebs=True, zones=ZONES, ami=None, os_version='10.10'):
    ec2_type = ec2_type or 'm1.small'
    instance_count = int(instance_count)
    if instance_count <= 0:
        return []

    bits = 32 if ec2_type == 'm1.small' else 64
    ebs = ebs or ec2_type == 't1.micro' # t1.micro requires ebs
    ami = ami or AMI[os_version][bits]['ebs' if ebs else 'ec2']
    security_groups = security_groups.split(',')
    image = ec2.get_all_images(image_ids=[ami])[0]

    logging.info("Starting %s instances using Ubuntu %s %d-bit AMI."
                 " EBS boot is %s." % (os_version, instance_count, bits, ebs))

    zones = zones.split(',') if isinstance(zones, str) else zones
    random.shuffle(zones)
    inst_bins = _bin(instance_count, len(zones))

    instances = []
    for bin, zone in zip(inst_bins, zones):
        if bin <= 0: continue

        rsvp = None
        tried_zones = set()
        while rsvp is None and len(tried_zones) < len(zones):
            try:
                rsvp = image.run(bin, bin, key_name=key, placement=zone,
                                 security_groups=security_groups,
                                 instance_type=ec2_type)
            except boto.exception.BotoServerError, e:
                tried_zones.add(zone)
                zone = random.choice(list(set(zones) - tried_zones))
        instances.extend(rsvp.instances)
        logging.info("Started %d instances in zone %s: %s" %
                     (bin, rsvp.instances[0].placement,
                      ", ".join([i.id for i in rsvp.instances])))

    _wait_on_instances_state(instances, 'running')

    for inst in instances:
        zone = inst.placement.split('-')
        name = '-'.join(('seamail', (zone[0][0] + zone[1][0] + zone[2]),
                         inst.id[2:]))
        inst.add_tag('Name', name)
        inst.add_tag('Seamail', VERSION)

    _wait_on_instances_ssh(instances)
    _call_on_instances(instances, configure, 'i386' if bits == 32 else 'amd64')

    return instances


def _bin(count, bins, start=0):
    return [count//bins + (1 if i < count % bins else 0) for i in xrange(bins)]


def _wait_on_instances_state(instances, state='running'):
    instances_ready = 0
    while instances_ready < len(instances):
        for i in range(10):
            instances_ready = 0
            for instance in instances:
                try:
                    instance.update()
                except boto.exception.EC2ResponseError:
                    continue
                if instance.state == state:
                    instances_ready += 1
            time.sleep(1)
            if instances_ready == len(instances):
                break
        logging.info('%d of %d instances %s' %
                     (instances_ready, len(instances), state))


def _wait_on_instances_ssh(instances):
    instances_ready = 0
    while instances_ready < len(instances):
        for i in range(10):
            instances_ready = 0
            for instance in instances:
                if _test_ssh(instance):
                    instances_ready += 1
            if instances_ready == len(instances):
                break
            time.sleep(1)
        logging.info('%d of %d instances accept connections' %
                     (instances_ready, len(instances)))
    time.sleep(10)


def _call_on_instances(instances, command, *args, **kwargs):
    _host_string = env.host_string
    for instance in instances:
        # Paramiko barfs on unicode strings. Convert to ascii.
        env.host_string = str(instance.public_dns_name)
        # Make 3 attempts at the command before giving up.
        for attempt in range(3):
            try:
                puts('Running "%s"' % command.__name__)
                command(*args, **kwargs)
                break
            except Exception, e:
                print e
                continue
    env.host_string = _host_string


def _test_ssh(instance):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        sock.connect((instance.public_dns_name, 22))
        subprocess.check_call(["ssh",
                               "-o", "StrictHostKeyChecking=no",
                               "-o", "PasswordAuthentication=no",
                               "-o", "ConnectTimeout=1",
                               "-i", env.key_filename,
                               "ubuntu@" + instance.public_dns_name, "uname"])
        return True
    except subprocess.CalledProcessError:
        return False
    except socket.timeout:
        return False
    except socket.error, e:
        return False
    finally:
        sock.close()
    return False


def ssh(idx=None):
    rsvps = ec2.get_all_instances()
    lst = []
    instances = [inst for rsvp in rsvps for inst in rsvp.instances]
    for instance in instances:
        if instance.state != 'running': 
            continue
        try:
            print "%d.\t%s%s%s" % (len(lst), instance.tags['Name'], 
                                   ' '* (48 - len(instance.tags['Name'])), 
                                   instance.public_dns_name)
            lst.append(instance)
        except (KeyError, AttributeError):
            continue
    
    while True:
        try:
            idx = int(idx or raw_input(": "))
            subprocess.call(["ssh", "-i", env.psh_key_filename, 
                             "-o", "StrictHostKeyChecking=no",
                             "-o", "PasswordAuthentication=no",
                             "%s@%s" % (env.psh_user, lst[idx].public_dns_name)],
                             stdin=sys.stdin, stdout=sys.stdout)
            break    
        except IndexError:
            idx = None
            print "No such instance. Please try again."
            continue
        except ValueError:
            print "Exiting..."
            break
