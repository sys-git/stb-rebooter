'''
Created on 19 Nov 2012

@author: francis
'''

from Rebooter.Core.Synchroniser.TransactionAborted import TransactionAborted
from Rebooter.Core.Synchroniser.TransactionFailed import TransactionFailed
from multiprocessing.synchronize import Semaphore, RLock
import itertools
import sys

class Synchroniser(object):
    """ 
    @summary: Makes inter-thread comms synchronous.
    """
    class Item(object):
        def __init__(self, i):
            self._i = i
            self._sem = Semaphore(0)
            self._result = []
        def acquire(self, timeout = None):
            return self._sem.acquire(block = True, timeout = timeout)
        def result(self, result):
            self._result.append(result)
            #    Now the result is complete, release it:
            self._sem.release()
        def getResult(self):
            return self._result.pop(0)
    def __init__(self):
        self._i = itertools.count(0)
        self._items = {}
        self._destroy = False
        self.__lock = RLock()
    def _lock(self):
        self.__lock.acquire()
    def _unlock(self):
        self.__lock.release()
    def isValidTransactionId(self, i):
        if (i is None):
            return False
        with self.__lock:
            return i in self._items.keys()
    def create(self, enabler = True):
        if not enabler: return
        with self.__lock:
            self.checkDestroyed()
            i = self._i.next()
            self._items[i] = self._getItem(i)
            return i
    def _getItem(self, i):
        return Synchroniser.Item(i)
    def acquire(self, i, timeout = None, purge = False):
        with self.__lock:
            self.checkDestroyed()
            try:
                item = self._items[i]
            except KeyError, _e:
                sys.stderr.write("Acquire on a non-existent synchroniser: %(I)s\n"%{"I":i})
                raise
        result = item.acquire(timeout = timeout)
        self.checkDestroyed()
        if not result:
            purge and self.purge(i)
            raise TransactionFailed(i)
        result = item.getResult()
        if purge:
            self.purge(i)
        return result
    def release(self, i, result = None):
        with self.__lock:
            self.checkDestroyed()
            try:
                item = self._items[i]
                item.result(result)
            except KeyError, _e:
                sys.stderr.write("Release on a non-existent synchroniser: %(I)s\n"%{"I":i})
                raise
    def getResult(self, i, purge = False):
        """ 
        @summary: Get the result of the synchroniser command:
        """
        with self.__lock:
            try:
                item = self._items[i]
            except KeyError, _e:
                sys.stderr.write("Result called on a non-existent synchroniser: %(I)s\n"%{"I":i})
                raise
            else:
                try:
                    result = item.getResult()
                except:
                    raise TransactionFailed()
                if purge == True:
                    self._items.pop(i)
                return result
    def purge(self, i):
        with self.__lock:
            self.checkDestroyed()
            try:
                self._items.pop(i)
            except Exception, _e:
                #    Don't care!
                pass
    def purgeAll(self):
        self._items = {}
    def releaseAll(self, result, purge = True, destroy=False):
        with self.__lock:
            for tId in self._items.keys():
                try:
                    self.release(tId, result)
                except Exception, _e:
                    #    Error triggering result in user handler.
                    pass
            if purge == True:
                self.purgeAll()
            self._destroy = destroy
    def destroy(self, exc=None):
        if exc==None:
            exc = TransactionAborted()
        self.releaseAll(exc, purge=True, destroy=True)
    def isDestroyed(self):
        with self.__lock:
            return self._destroy
    def checkDestroyed(self):
        with self.__lock:
            if self._destroy==True:
                raise TransactionAborted()
