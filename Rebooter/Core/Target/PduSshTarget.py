'''
Created on 13 Nov 2012

@author: francis
'''

from Rebooter.Core.Target.BasePduTarget import BasePduTarget
from Rebooter.Core.Target.BaseSshTarget import BaseSshTarget

class PduSshTarget(BasePduTarget, BaseSshTarget):
    def __init__(self, *args, **kwargs):
        BasePduTarget.__init__(self, *args, **kwargs)
        BaseSshTarget.__init__(self, *args, **kwargs)
    def __str__(self):
        return "PduSshTarget (%(H)s:%(P)s)"%{"H":self.host(), "P":self.port()}
