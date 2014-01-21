# -*- coding: utf-8 -*-
"""
dynpool
=======

`dynpool <https://tabo.pe/projects/dynpool/>`_ is a Python
library that handles the growing and shrinking of a pool
of resources depending on usage patterns,
written by `Gustavo Picón <https://tabo.pe/>`_ and
licensed under the Apache License 2.0.

``dynpool`` doesn't handle pools directly, and has no
concept of connections, threads or processes. That should be
dealt in a provided pool object. ``dynpool`` only handles
the growing and shrinking of resources in the given pool
object, and for that, the pool must follow an interface:


.. py:class:: PoolInterface


   .. py:attribute:: size

      The number of resources in the pool at the moment. Includes
      idle and used resources.

   .. py:attribute:: idle

      The number of idle resources in the pool at the moment.
      ``dynpool`` will either :py:meth:`grow` or :py:meth:`shrink`
      idle resources depending on the values of
      `minspare` and `maxspare` in :py:class:`dynpool.DynamicPoolResizer`.

   .. py:attribute:: min

      The minimum number of resources that should be in the pool.
      ``dynpool`` will :py:meth:`grow` the pool if :py:attr:`size`
      is lower than this value.


   .. py:attribute:: max

      The minimum number of resources that should be in the pool.
      ``dynpool`` won't grow the pool beyond this point, and will
      try to :py:meth:`shrink` it as soon as resources are freed.

      If max has a negative value, there won't be a limit for
      resource growth.

   .. py:attribute:: qsize

      The size of the incoming jobs queue that will be handled by
      idle resources.

   .. py:method:: grow(amount)

      Creates ``amount`` new idle resources in the pool.

   .. py:method:: shrink(amount)

      Shrinks the pool by ``amount`` resources.


Example

.. code-block:: python

    import dynpool
    from example_code import SomeThreadPool, run_periodically

    # A user provided thread pool that follows the interface
    # expected by DynamicPoolResizer.
    pool = SomeThreadPool(min=3, max=30)

    # We create a thread pool monitor.
    monitor = dynpool.DynamicPoolResizer(pool, minspare=5, maxspare=10)

    # Creating a thread pool monitor does nothing. We need to
    # call it's run() method periodically. Let's do it every second.
    run_periodically(monitor.run, interval=1)


``dynpool`` has been tested in Python 2.6, 2.7, 3.2, 3.3 and
PyPy 2.2. Other versions may work but are not supported.



"""

__version__ = '1.0'

import math
import threading
import time


class DynamicPoolResizer(object):
    """Grow or shrink a pool of resources depending on usage patterns.

    :param pool: Pool object that follows the expected interface.
    :param minspare: Minimum number of idle resources available.
    :param maxspare: Maximum number of idle resources available.
    :param shrinkfreq: Minimum seconds between shrink operations.
    :param logger: Callback that will act as a logger. There is no
                   logging by default
    :param mutex: Mutex used in :py:meth:`run()`.
                  A `threading.Lock()` object will be used by default.
    """
    def __init__(self, pool, minspare, maxspare, shrinkfreq=5,
                 logger=None, mutex=None):
        self.pool = pool
        self.minspare = minspare
        self.maxspare = maxspare
        self.shrinkfreq = shrinkfreq
        self.log = logger or (lambda msg: None)
        self.lastshrink = None
        self._mutex = mutex or threading.Lock()

    def run(self):
        """Perform maintenance operations.

       This method should be called periodically by a running application.
       """
        with self._mutex:
            grow_value = self.grow_value
            if grow_value:
                self.grow(grow_value)
            elif self.can_shrink():
                shrink_value = self.shrink_value
                if shrink_value:
                    self.shrink(shrink_value)

    def action_log(self, action, amount):
        pool = self.pool
        self.log(
            'Thread pool: [current={0}/idle={1}/queue={2}] {3} by {4}'.format(
                pool.size, pool.idle, pool.qsize, action, amount))

    @property
    def grow_value(self):
        pool = self.pool
        pool_size = pool.size
        pool_min = pool.min
        pool_max = pool.max
        pool_idle = pool.idle
        maxspare = self.maxspare
        if 0 < pool_max <= pool_size or pool_idle > maxspare:
            growby = 0
        elif not pool_idle and pool.qsize:
            # UH OH, we don't have available threads to continue serving the
            # queue. This means that we just received a lot of requests that we
            # couldn't handle with our usual minspare threads value, so to
            # avoid more problems, quickly grow the pool by the maxspare value.
            self.log('Threads exhausted and connection queue not empty!')
            growby = maxspare
        else:
            growby = max(0, pool_min - pool_size, self.minspare - pool_idle)
        return growby

    def grow(self, growby):
        self.action_log('Growing', growby)
        self.pool.grow(growby)

    def can_shrink(self):
        last = self.lastshrink
        return not last or time.time() - last > self.shrinkfreq

    @property
    def shrink_value(self):
        pool = self.pool
        pool_size = pool.size
        pool_min = pool.min
        pool_idle = pool.idle
        pool_qsize = pool.qsize
        minspare = self.minspare
        if pool_size > pool_min and pool_size == pool_idle and not pool_qsize:
            # It's oh so quiet...
            # All the threads are idle and there are no incoming requests.
            # We go down to our initial threadpool size.
            shrinkby = min(pool_size - pool_min, pool_idle - minspare)
        elif pool_idle > self.maxspare:
            # Leave only maxspare idle threads ready to accept connections.
            shrinkby = pool_idle - self.maxspare
        elif pool_idle > minspare and not pool_qsize:
            # We have more than minspare threads idling, but no incoming
            # connections to handle. Slowly shrink the thread pool by half
            # every time the Thread monitor runs (as long as there are no
            # incoming connections).
            shrinkby = int(math.ceil((pool_idle - minspare) / 2.0))
        else:
            shrinkby = 0
        return shrinkby

    def shrink(self, shrinkby):
        self.action_log('Shrinking', shrinkby)
        self.pool.shrink(shrinkby)
        self.lastshrink = time.time()
