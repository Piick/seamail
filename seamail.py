#!/usr/bin/env python
# encoding: utf-8
"""
seamail.py

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


from boto.exception import BotoServerError
from boto.sqs.jsonmessage import JSONMessage
from mixpanel import MixpanelEmail
import boto
import logging
import random
import smboto
import time
import tornado.template


options = {'from_name': 'FamilyLink',
           'from_email': 'specials@familylink.com',
           'return_path': 'familylink@piick.com',
           'mp_token': '8fc924b425bc036d2b189712ee63acee',
           'aws_access_key': 'AKIAJLNQDI4ZRRGGE6IA',
           'aws_secret_key': '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'}


ec2 = boto.connect_ec2(options['aws_access_key'], options['aws_secret_key'])
sqs = boto.connect_sqs(options['aws_access_key'], options['aws_secret_key'])
ses = smboto.connect_ses(options['aws_access_key'], options['aws_secret_key'])


def process_queue():
    q = sqs.create_queue('seamail')
    q.set_message_class(JSONMessage)

    loader = tornado.template.Loader("/opt/seamail/templates")
    from_address = "%s <%s>" % (options['from_name'], options['from_email'])

    while True:
        send_period, send_quota = get_send_quota()
        logging.error('New quotas: %f\t%d' % (send_period, send_quota))
        next_send_time = time.time()
        while send_quota > 0:
            rs = q.get_messages(10)
            for msg in rs:
                sent_time = send_message(next_send_time, loader, 
                                         from_address, msg)
                if sent_time:
                    next_send_time = sent_time + send_period
                    send_quota -= 1
                else:
                    # If the message didn't send, put it at the back of the line
                    # with an incremented tries count.
                    new_msg = msg.get_body()
                    new_msg[4] += 1
                    q.write(JSONMessage(body=new_msg))
                msg.delete()
        time.sleep(60 + random.randint(0, 60))


def send_message(send_time, loader, from_address, msg):
    template, name, email, context, tries = msg.get_body()
    context.update({'email': email, 'name': name})
    content = loader.load("%s.html" % template).generate(**context)
    subject, body = content.split('------NOTIFICATION_DELIMITER------')
    to_address = "%s <%s>" % (name, email.strip())

    # Get the Mixpanel instrumented bodies.
    if options['mp_token']:
        mixpanel_html = MixpanelEmail(options['mp_token'], template)
        body = mixpanel_html.add_tracking(to_address, body.strip())

    # Wait until our next scheduled slot to send the mail.
    sleep_time = (send_time - time.time())
    time.sleep(sleep_time if sleep_time > 0 else 0)

    try:
        # Send the email and report the sent_time.
        ses.send_email(utf8(from_address), utf8(subject.strip()), 
                       utf8(body.strip()), [utf8(to_address)], format='html', 
                       return_path=options['return_path'])
        logging.error('%d\t%s sent' % (time.time(), to_address))
        return time.time()
    except BotoServerError:
        logging.error('Unable to send %s to %s with %s' % 
                      (template, to_address, context))
        return 0


def get_send_quota():
    num_senders = get_num_senders()
    try:
        stat = ses.get_send_quota()
        stat = stat['GetSendQuotaResponse']['GetSendQuotaResult']

        send_rate = float(stat['MaxSendRate'])
        max_send = int(float(stat['Max24HourSend']))
        sent = int(float(stat['SentLast24Hours']))

        return ((1 / send_rate) * num_senders, (max_send - sent) / num_senders)
    except KeyError:
        return (1.0 * num_senders, 1000 / num_senders)


def get_num_senders():
    rsvps = ec2.get_all_instances()
    lst = []
    for rsvp in rsvps:
      for inst in rsvp.instances:
        if inst.state == 'running' and 'Seamail' in inst.tags:
          lst.append(inst.public_dns_name)
    return len(lst) * 1


def utf8(value):
    if isinstance(value, unicode):
        return value.encode("utf-8")
    assert isinstance(value, str)
    return value


process_queue()
