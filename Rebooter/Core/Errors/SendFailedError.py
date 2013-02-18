'''
Created on 15 Nov 2012

@author: francis
'''

class SendFailedError(Exception):
    def __init__(self, msg):
        super(SendFailedError, self).__init__(msg)
        self._msg = msg
    def msg(self):
        return self._msg
