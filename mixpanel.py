#!/usr/bin/env python
#
# Mixpanel, Inc. -- http://mixpanel.com/
#
# This library is used for adding tracking code to HTML email bodies.

try:
    import json
except ImportError:
    import simplejson as json
import urllib
import urllib2

class MixpanelEmail:

    ENDPOINT = 'http://api.mixpanel.com/email'

    def __init__(self, token, campaign, type='html', properties=None, redirect_host=None, click_tracking=True):
        self.params = {}
        self.params['token'] = token
        self.params['campaign'] = campaign
        if type == 'text':
            self.params['type'] = 'text'
        if properties:
            self.params['properties'] = json.dumps(properties)
        if redirect_host:
            self.params['redirect_host'] = redirect_host
        if not click_tracking:
            self.params['click_tracking'] = '0'

    def add_tracking(self, distinct_id, body):
        p = self.params.copy()
        p['distinct_id'] = distinct_id
        p['body'] = body
        encoded = self.unicode_urlencode(p)
        rewritten = urllib2.urlopen(self.ENDPOINT, encoded).read()
        return rewritten

    def unicode_urlencode(self, params):
        if isinstance(params, dict):
            params = params.items()
        for i, k in enumerate(params):
            if isinstance(k[1], list):
                params[i] = (k[0], json.dumps(k[1]),)
        return urllib.urlencode([(k, isinstance(v, unicode) and v.encode('utf-8') or v) for k, v in params])

if __name__ == '__main__':
    api = MixpanelEmail(
        'YOUR TOKEN HERE',
        'YOUR CAMPAIGN HERE',
        #type='text',
        #properties={'name1': 'value1', 'name2': 'value2'},
        #redirect_host='OPTIONAL REDIRECT_HOST HERE',
    )
    example = \
'''
<p>Hi User,</p>
<p>This is a sample email from <a href="http://example.com/">example.com</a>.</p>
<p>Each anchor link will be replaced with a tracking redirect when filtered with
<a href="http://mixpanel.com/">Mixpanel's</a> email tracking service.</p>
--<br>
Signature<br>
'''
    rewritten = api.add_tracking('test_user@example.com', example)
    print rewritten
