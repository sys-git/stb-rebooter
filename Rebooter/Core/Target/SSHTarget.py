'''
Created on 13 Nov 2012

@author: francis
'''

from Rebooter.Core.Target.BaseSshTarget import BaseSshTarget

class SSHTarget(BaseSshTarget):
    def __str__(self):
        return "SSHTarget (%(H)s:%(P)s)"%{"H":self.host(), "P":self.port()}
