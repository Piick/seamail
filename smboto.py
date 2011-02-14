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


from boto.ses import SESConnection


class SeamailSESConnection(SESConnection):
    """Override SESConnection to allow the reply_address argument to 
    SendEmail."""
    
    def send_email(self, source, subject, body, to_addresses, cc_addresses=None,
                   bcc_addresses=None, format='text', return_path=None):
        params = {
            'Source': source,
            'Message.Subject.Data': subject,
        }

        if return_path:
            params['ReturnPath'] = return_path
            
        format = format.lower().strip()
        if format == 'html':
            params['Message.Body.Html.Data'] = body
        elif format == 'text':
            params['Message.Body.Text.Data'] = body
        else:
            raise ValueError("'format' argument must be 'text' or 'html'")

        self._build_list_params(params, to_addresses,
                               'Destination.ToAddresses.member')
        if cc_addresses:
            self._build_list_params(params, cc_addresses,
                                   'Destination.CcAddresses.member')

        if bcc_addresses:
            self._build_list_params(params, bcc_addresses,
                                   'Destination.BccAddresses.member')

        return self._make_request('SendEmail', params)


def connect_ses(aws_access_key_id=None, aws_secret_access_key=None, **kwargs):
    """
    :type aws_access_key_id: string
    :param aws_access_key_id: Your AWS Access Key ID

    :type aws_secret_access_key: string
    :param aws_secret_access_key: Your AWS Secret Access Key

    :rtype: :class:`boto.ses.SESConnection`
    :return: A connection to Amazon's SES
    """
    return SeamailSESConnection(aws_access_key_id, aws_secret_access_key, 
                                **kwargs)
