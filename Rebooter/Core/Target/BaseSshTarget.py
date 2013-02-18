'''
Created on 13 Nov 2012

@author: francis
'''

from Rebooter.Core.Target.BaseTarget import BaseTarget
from Rebooter.Impl.Ssh.SshType import SshType

class BaseSshTarget(BaseTarget):
    DEFAULT_SENDBUFFERTIMEOUT = 0
    DEFAULT_POSTCONNECTIONTIMEOUT = 0
    DEFAULT_PORT = 22
    DEFAULT_SSHTYPE = SshType.STB
    def __init__(self, host, **kwargs):
        self._host = host
        self._port = kwargs.get("port", BaseSshTarget.DEFAULT_PORT)
        self._username = kwargs.get("username", None)
        self._password = kwargs.get("password", None)
        self._postConnectionTimeout = kwargs.get("postConnectionTimeout", BaseSshTarget.DEFAULT_POSTCONNECTIONTIMEOUT)
        self._sendBufferTimeout = kwargs.get("sendBufferTimeout", BaseSshTarget.DEFAULT_SENDBUFFERTIMEOUT)
        self._sshType = kwargs.get("sshType", BaseSshTarget.DEFAULT_SSHTYPE)
    def host(self):
        return self._host
    def port(self):
        return self._port
    def username(self):
        return self._username
    def password(self):
        return self._password
    def postConnectionTimeout(self):
        return self._postConnectionTimeout
    def sendBufferTimeout(self):
        return self._sendBufferTimeout
    def sshType(self):
        return self._sshType
    def uId(self):
        r"""
        @summary: Return a hashable uId for this host:port combo.
        """
        return str(self)
