'''
Created on 13 Nov 2012

@author: francis
'''

class BaseTarget(object):
    @classmethod
    def uId(cls):
        raise NotImplementedError("%(C)s::uId"%{"C":cls})
