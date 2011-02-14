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
import smboto
import tornado.template


options = {'from_name': 'Piick.com',
           'from_email': 'piick@piick.com',
           'mp_token': '',
           'aws_access_key': '',
           'aws_secret_key': ''}


sqs = boto.connect_sqs(options['aws_access_key'], options['aws_secret_key'])
ses = smboto.connect_ses(options['aws_access_key'], options['aws_secret_key'])


def process_queue():
    q = sqs.create_queue('seamail')
    q.set_message_class(JSONMessage)

    loader = tornado.template.Loader("/opt/seamail/templates")
    from_address = "%s <%s>" % (options['from_name'], options['from_email'])
    
    while True:
        rs = q.get_messages(10)
        for msg in rs:
            send_message(loader, from_address, *msg.get_body())
            msg.delete()


def send_message(loader, from_address, template, name, email, context):
    context.update({'email': email, 'name': name})
    content = loader.load("%s.html" % template).generate(**context)
    subject, body = content.split('------NOTIFICATION_DELIMITER------')
    to_address = "%s <%s>" % (name, email.strip())

    # Get the Mixpanel instrumented bodies.
    if options['mp_token']:
        mixpanel_html = MixpanelEmail(options['mp_token'], template)
        body = mixpanel_html.add_tracking(to_address, body.strip())

    try:
        ses.send_email(from_address, subject.strip(), body.strip(), 
                       [to_address], format='html', return_path=to_address)
        return True
    except BotoServerError:
        logging.error('Unable to send %s to %s with ' % 
                      (template, to_address, context))
        return False


process_queue()