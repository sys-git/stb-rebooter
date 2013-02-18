'''
Created on 19 Nov 2012

@author: francis
'''

from Rebooter.Core.Target.BaseTarget import BaseTarget

class BasePduTarget(BaseTarget):
    def __init__(self, *args, **kwargs):
        self._mapping = kwargs.pop("mapping", {})
    def mapping(self):
        return self._mapping
    def setMapping(self, mapping):
        self._mapping = mapping
