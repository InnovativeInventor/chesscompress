import resource
import time
import random
import functools
import itertools
import logging
import threading
from queue import Empty, Full
from collections import defaultdict
import dill
import multiprocessing as mp

from pystreams.worker import Worker, End, EmptyBuffers, NoKey
from pystreams.util import *

mp.set_start_method('fork')
#print("getrlimit before:", resource.getrlimit(resource.RLIMIT_NOFILE))
resource.setrlimit(resource.RLIMIT_NOFILE, (2**12, 2**62))


class Stream:
    def __init__(self, data=None, n=None):
        if n is None:
            n = mp.cpu_count()
        self.n = n
        # We want to limit the memory consumption, but we can only safely do it
        # at the feeding level

        self.work_queue = mp.JoinableQueue()
        self.layers = []
        self.pool = []
        self.signal_queues = []
        self.feed_thread = None
        self.started = False
        self.cancelled = False
        if data is not None:
            self._data(data)
        self.cleanup_thread = None

    def _start(self):
        assert not self.started
        self.started = True
        logging.info(f'Starting {self.n} processes')
        self.signal_queues = [mp.JoinableQueue() for _ in range(self.n)]
        for i in range(self.n):
            w = Worker(i, self.work_queue, self.signal_queues, self.layers)
            w.start()
            self.pool.append(w)

    def _stop(self):
        # Actually this is more like a join: it waits for everything to finish
        # on its own accord and cleans up nicely afterwards.

        assert self.started
        # It's safe to wait for the feeding thread, since the other processes
        # will make sure to empty its queue so it can finish.
        logging.info('waiting for done feeding')
        self.feed_thread.join()

        # We wait for the queues to settle before sending EmptyBuffers,
        # so the buffers have a chance to actually work.
        logging.info('waiting for worker queue join')
        self.work_queue.join()

        logging.info('telling workers to empty buffers')
        for signals in self.signal_queues:
            signals.put(EmptyBuffers, timeout=LONG_TIMEOUT)
        logging.info('making sure the message is received')
        for signals in self.signal_queues:
            signals.join()

        logging.info('waiting for work_queue again')
        self.work_queue.join()

        logging.info('sending End')
        for signals in self.signal_queues:
            signals.put(End, timeout=LONG_TIMEOUT)
        logging.info('waiting for processes')
        for w in self.pool:
            w.join()
            w.terminate()

        logging.info('closing')
        for closable in self.signal_queues + self.pool + [self.work_queue]:
            closable.close()
        for queue in self.signal_queues + [self.work_queue]:
            queue.join_thread()

        logging.info('stream closed')

    def _cancel(self):
        logging.info('(cancel) waiting for feed thread to stop')
        self.cancelled = True
        logging.info('trying to unblock queues')
        for queue in [self.work_queue]:
            while True:
                try:
                    queue.get_nowait()
                except Empty:
                    break
                else:
                    queue.task_done()
        logging.info('stream cancelled')

    def _run(self):
        self._start()
        self._stop()

    def _data(self, it, chunksize=None, close=False):
        if chunksize is None:
            if hasattr(it, '__len__'):
                chunksize = max(len(it) // self.n, 1)
            else:
                chunksize = CHUNK_SIZE

        def inner():
            logging.debug('starting feeding thread')
            for i, chunk in enumerate(slice(it, chunksize)):
                if self.cancelled:
                    break
                self.work_queue.put((0, chunk), timeout=LONG_TIMEOUT)
            if close:
                # TODO: Use `with` instead
                it.close()
        self.feed_thread = threading.Thread(target=inner)
        # We make sure all data is feed by calling
        # self.feed_thread_join() in _stop
        self.feed_thread.start()
        return self

    def lines(self, file):
        self._data(file, close=True)
        return self

    def collect(self, from_chunk, combine, finisher=None):
        # Should really repeat `from_objects` till number of chunks is small enough
        combine_many = functools.partial(functools.reduce, combine)
        res = combine_many(self.reduce_once(from_chunk).reduce_once(combine_many))
        if finisher is not None:
            return finisher(res)
        return res

    def chunk_by_key(self, key_function):
        def inner(chunk):
            for x in chunk:
                yield (key_function(x), (x,))
        self.layers.append(inner)
        return self

    def map(self, f):
        def inner(chunk):
            yield (NoKey, map(f, chunk))
        self.layers.append(inner)
        return self

    def filter(self, f):
        def inner(chunk):
            yield (NoKey, filter(f, chunk))
        self.layers.append(inner)
        return self

    def shuffle(self, chunks=None):
        if chunks is None:
            chunks = SHUFFLE_CHUNKS
        self.chunk_by_key(lambda x: hash(x) % chunks)

        def shuffled(tup):
            l = list(tup)
            random.shuffle(l)
            return l
        return self.chunkmap(shuffled)

    def distinct(self, chunks=None):
        if chunks is None:
            chunks = SHUFFLE_CHUNKS
        return (self
                .chunk_by_key(lambda x: hash(x) % chunks)
                .reduce_once(lambda chunk: len(set(chunk)))
                .sum())

    def flatmap(self, f):
        def inner(chunk):
            for x in chunk:
                # TODO: What if the result of `f` is very large, or infinite?
                # In that case it would be nice to use the feeder thread and queue
                # to slowly ingest the data as space becomes available.

                # TODO: Can we be smarter if f(x) is itself a Stream?
                # In Java, if f(x) is a stream, it is changed to a sequential stream.
                # We currently don't have a way to convert however.
                # Also, the Java streams are lazy, so flatmapping to an infinite
                # stream works. Currently we can only flatmap to EagerStream.
                yield (NoKey, f(x))
        self.layers.append(inner)
        return self

    def map_chunks(self, f):
        def inner(chunk):
            yield (NoKey, f(chunk))
        self.layers.append(inner)
        return self

    def reduce_once(self, f):
        def inner(chunk):
            yield (NoKey, (f(chunk),))
        self.layers.append(inner)
        return self

    def reduce(self, f, unit):
        def inner(chunk):
            yield (NoKey, (functools.reduce(f, chunk, unit),))
        self.layers.append(inner)
        return functools.reduce(f, self, unit)

    def peek(self, f):
        """ Returns a stream consisting of the elements of this stream, additionally performing the provided action on each element as elements are consumed from the resulting stream. """
        def inner(chunk):
            for x in chunk:
                f(x)
                yield (NoKey, (x,))
        self.layers.append(inner)
        return self

    def foreach(self, f):
        # Note that foreach calls the functioin from different processes.
        def inner(chunk):
            for x in chunk:
                f(x)
            yield from ()
        self.layers.append(inner)
        self._run()

    def take_one(self, otherwise=None):
        return next(self.take(1), otherwise)

    def take(self, n):
        q = mp.Queue(n)

        def inner(chunk):
            try:
                q.put_nowait(chunk)
            except Full:
                return
            yield from ()
        self.layers.append(inner)

        self._start()

        def stop_then_end():
            # _stop ensures that all the calls to inner() has been made.
            self._stop()
            try:
                q.put_nowait(End)
            except Full:
                pass
            time.sleep(.1)  # Python bug https://bugs.python.org/issue35844
            q.close()
            q.join_thread()
        self.cleanup_thread = threading.Thread(target=stop_then_end)
        self.cleanup_thread.start()

        i = 0
        while i < n:
            chunk = q.get(timeout=LONG_TIMEOUT)
            if chunk is End:
                break
            # Take at most n-i values from the chunk
            for x, _ in zip(chunk, range(n - i)):
                yield x
                i += 1
        else:
            # If we got through the loop (but not the stream)
            # Note: Can this interact badly with _stop?
            self._cancel()

        self.cleanup_thread.join()

    def take_stream(self, n):
        # TODO: This currently does no cancelling of the remaining values.
        # They are simply not let through.
        seen = mp.Value('i', 0)

        def inner(chunk):
            nonlocal seen
            if seen.value > n:
                return
            seen.value += len(chunk)
            yield (NoKey, chunk)
        self.layers.append(inner)
        return self

    def __iter__(self):
        """ Iterable implementation which merges all chunks in the main thread. """
        q = mp.Queue()

        def inner(chunk):
            # The queue here could potentially be full, if the iterator is slow
            # at consuming the vaues. However in that case it's presumably fine
            # to potentially halt the computation of new vaules.
            q.put(chunk, timeout=LONG_TIMEOUT)
            yield from ()
        self.layers.append(inner)

        self._start()

        def stop_then_end():
            # _stop ensures that all the calls to inner() has been made.
            self._stop()
            q.put(End, timeout=LONG_TIMEOUT)
            time.sleep(.1)  # Python bug https://bugs.python.org/issue35844
            q.close()
            q.join_thread()
        self.cleanup_thread = threading.Thread(target=stop_then_end)
        # self.cleanup_thread.setDaemon(True)
        self.cleanup_thread.start()

        while True:
            chunk = q.get(timeout=LONG_TIMEOUT)
            if chunk is End:
                break
            yield from chunk

        # Warning: This cleanup code may not run if the iterator is abandoned.
        self.cleanup_thread.join()

    def any(self):
        q = mp.Queue()

        def inner(chunk):
            if any(chunk):
                q.put_nowait(True)
            yield from ()
        self.layers.append(inner)
        self._start()

        def stop_then_end():
            self._stop()  # Wait for everything to settle down
            try:
                q.put_nowait(False)  # Didn't find anything
            except AssertionError as e:
                assert q._closed
        self.cleanup_thread = threading.Thread(target=stop_then_end)
        # self.cleanup_thread.setDaemon(True)
        self.cleanup_thread.start()

        res = q.get(timeout=LONG_TIMEOUT)
        if res:
            self._cancel()

        # Cleanup
        q.close()
        q.join_thread()
        self.cleanup_thread.join()

        return res

    def all(self):
        return not self.map(lambda x: not bool(x)).any()

    def count(self):
        return sum(self.reduce_once(len))

    def sum(self):
        return sum(self.reduce_once(sum))

    def min(self):
        return min(self.reduce_once(min))

    def max(self):
        return max(self.reduce_once(max))


class SequentialStream:
    def __init__(self, data=None):
        self.data = data

    def filter(self, f):
        self.data = filter(f, self.data)
        return self

    def map(self, f):
        self.data = map(f, self.data)
        return self

    def flatmap(self, f, lazy=True):
        if lazy:
            self.data = itertools.chain(map(f, self.data))
        else:
            self.data = sum(map(f, self.data), [])
        return self

    def sum(self):
        return sum(self.data)

    def count(self):
        return len(list(self.data))

    def foreach(self, f):
        for x in self.data:
            f(x)

    def __iter__(self):
        return iter(self.data)

# The advantage of EagerStream is probably in how well it pickles


class EagerStream:
    def __init__(self, data=None):
        self.data = data

    def filter(self, f):
        self.data = list(filter(f, self.data))
        return self

    def map(self, f):
        self.data = list(map(f, self.data))
        return self

    def flatmap(self, f):
        self.data = sum(map(list, map(f, self.data)), [])
        return self

    def sum(self):
        return sum(self.data)

    def count(self):
        return len(list(self.data))

    def foreach(self, f):
        for x in self.data:
            f(x)

    def __iter__(self):
        return iter(self.data)


class FunctionalStream:
    def __init__(self, data=None):
        self.data = data

    def filter(self, f):
        return FunctionalStream(filter(f, self.data))

    def map(self, f):
        return FunctionalStream(map(f, self.data))

    def flatmap(self, f):
        return FunctionalStream(itertools.chain(map(f, self.data)))

    def sum(self):
        return sum(self.data)

    def count(self):
        return len(list(self.data))

    def foreach(self, f):
        for x in self.data:
            f(x)

    def __iter__(self):
        return iter(self.data)
