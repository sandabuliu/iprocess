#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import Queue
import logging
import traceback
import threading
from functools import wraps

import multiprocess as multiprocessing


__author__ = 'tong'

logger = logging.getLogger('interactive')


class IError(Exception):
    def __init__(self, **response):
        self.status = response['status']
        self.exception = response['data']
        self.traceback = response.get('traceback')

    def __str__(self):
        return 'status: %s\ndata: %s\ntraceback: %s' % \
               (self.status, self.exception, self.traceback)


class IProcess(multiprocessing.Process):
    def __init__(self, thread=None, *args, **kwargs):
        super(IProcess, self).__init__(*args, **kwargs)
        self._thread = thread or 1
        self._pool = multiprocessing.Queue(self._thread)
        self._threads = []
        self._requests = []
        self._states = {}
        for i in range(self._thread):
            request, response = multiprocessing.Queue(), multiprocessing.Queue()
            t = threading.Thread(target=self.loop, args=(request, response), name='request-%s' % i)
            self._threads.append(t)
            self._requests.append((request, response))
            self._pool.put(i)
            self._states[t.name] = None

        self._reader_mutex = multiprocessing.Lock()
        self._reader = multiprocessing.Queue(), multiprocessing.Queue()
        self._threads.append(threading.Thread(target=self.loop, args=self._reader, name='reader'))
        self._states['reader'] = None

        self._collection = multiprocessing.Queue()
        self._received = multiprocessing.Event()
        self._properties = {}
        for key in dir(self.__class__):
            value = getattr(self.__class__, key, None)
            value = getattr(value, '__doc__', None)
            if str(value).startswith('child_property.'):
                self._properties[key] = None
            if str(value).startswith('child_timer.'):
                delta = int(value.split('.')[-1])
                self._threads.append(threading.Thread(target=self.timentry, args=(key, delta),
                                                      name='timer.%s' % key))
        self._wrap_run()

    @property
    def interfaces(self):
        if not self.pid or self.pid == os.getpid():
            states = self._states.copy()
            for k, v in states.items():
                if v and v.get('time'):
                    states[k]['duration'] = (time.time() - v.pop('time')) * 1000
            return states
        if not self.is_alive():
            return None
        try:
            if self._reader_mutex.acquire(timeout=0.1):
                request, response = self._reader
                request.put(('interfaces', (), {}))
                rep = self.wait(response)
                self._reader_mutex.release()
            else:
                rep = self.interactive('interfaces')
            if rep['status'] == 200:
                return rep['data']
            else:
                raise IError(**rep)
        except IError, e:
            if e.status == 502 and self._received.is_set():
                return self._properties.get('interfaces')
            raise

    @property
    def keepalive(self):
        if not self.pid:
            raise Exception('The process has not started')

        ret = {'alive': self.is_alive()}
        if self._received.is_set():
            ret.update(self._properties.get('__error__', {}))
        if not ret['alive']:
            ret['exitcode'] = self.exitcode
        return ret

    def wait(self, queue):
        while True:
            try:
                return queue.get(timeout=2)
            except Queue.Empty:
                if not self.is_alive():
                    raise IError(status=502, data='service is died(exitcode: %s)' % self.exitcode)

    def interactive(self, func_name, *args, **kwargs):
        index = self.wait(self._pool)
        request, response = self._requests[index]
        request.put((func_name, args, kwargs))
        rep = self.wait(response)
        self._pool.put(index)
        return rep

    def _wrap_run(self):
        run = self.run
        c = threading.Thread(target=self.collect)
        c.setDaemon(True)
        c.start()

        @wraps(run)
        def _func():
            for t in self._threads:
                t.setDaemon(True)
                t.start()

            ret = None
            try:
                ret = run()
            except Exception, e:
                self._properties['__error__'] = {
                    'error': e, 'traceback': traceback.format_exc()
                }

            for p in self._properties:
                self._properties[p] = getattr(self, p, self._properties.get(p))
            self._collection.put(self._properties)
            return ret
        self.run = _func

    def collect(self):
        self._properties = self._collection.get()
        self._received.set()

    def loop(self, request, response):
        while True:
            req = request.get()
            name = threading.currentThread().name
            logger.info('request: %s' % (req, ))
            func_name, args, kwargs = req
            self._states[name] = {'time': time.time(), 'func': func_name, 'args': args, 'kwargs': kwargs}
            rep = self.handle(func_name, *args, **kwargs)
            response.put(rep)
            logger.info('response: %s' % (rep, ))
            self._states[name] = None

    def handle(self, func_name, *args, **kwargs):
        try:
            value = getattr(self, func_name)
            if callable(value):
                return {'status': 200, 'data': value(*args, **kwargs)}
            else:
                return {'status': 200, 'data': value}
        except TypeError, e:
            return {'status': 400, 'data': e, 'traceback': traceback.format_exc()}
        except Exception, e:
            return {'status': 500, 'data': e, 'traceback': traceback.format_exc()}

    @classmethod
    def child(cls, func):
        @wraps(func)
        def _func(self, *args, **kwargs):
            if self.pid == os.getpid():
                return func(self, *args, **kwargs)
            if not self.is_alive():
                raise IError(status=502, data='service is died(exitcode: %s)!' % self.exitcode)
            rep = self.interactive(func.__name__, *args, **kwargs)
            if rep['status'] == 200:
                return rep['data']
            raise IError(**rep)
        return _func

    @classmethod
    def property(cls, func):
        func.__doc__ = 'child_property.%s' % func.__name__

        @property
        @wraps(func)
        def _func(self):
            if not self.pid or self.pid == os.getpid():
                return func(self)
            if not self.is_alive() and self._received.is_set():
                return self._properties.get(func.__name__)
            try:
                if self._reader_mutex.acquire(timeout=0.1):
                    request, response = self._reader
                    request.put((func.__name__, (), {}))
                    rep = self.wait(response)
                    self._reader_mutex.release()
                else:
                    rep = self.interactive(func.__name__)
                if rep['status'] == 200:
                    return rep['data']
                raise IError(**rep)
            except IError, e:
                if e.status == 502 and self._received.is_set():
                    return self._properties.get(func.__name__)
                raise
        return _func

    @classmethod
    def timer(cls, delta):
        def _timer(func):
            func.__doc__ = 'child_timer.%s' % delta
            return func
        return _timer

    def timentry(self, func_name, delta):
        while True:
            try:
                logger.info('cleaner next timer wait %ss' % delta)
                time.sleep(delta)
                func = getattr(self, func_name)
                ret = func()
                if isinstance(ret, (int, float, long)) and ret > 0:
                    delta = ret
            except Exception, e:
                logger.error('cleaner handler: %s' % e, exc_info=True)
