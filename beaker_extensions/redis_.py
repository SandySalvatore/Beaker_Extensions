import logging
from beaker.exceptions import InvalidCacheBackendError

from beaker_extensions.nosql import Container
from beaker_extensions.nosql import NoSqlManager
from beaker_extensions.nosql import pickle

try:
    from redis import StrictRedis
except ImportError:
    raise InvalidCacheBackendError("Redis cache backend requires the 'redis' library")

log = logging.getLogger(__name__)

class RedisManager(NoSqlManager):
    def __init__(self, namespace, url=None, data_dir=None, lock_dir=None, **params):
        self.connection_pool = params.pop('connection_pool', None)
        NoSqlManager.__init__(self, namespace, url=url, data_dir=data_dir, lock_dir=lock_dir, **params)

    def open_connection(self, host, port, **params):
        self.db_conn = StrictRedis(host=host, port=int(port), connection_pool=self.connection_pool, **params)

    def __contains__(self, key):
        log.debug('%s contained in redis cache (as %s) : %s'%(key, self._format_key(key), self.db_conn.exists(self._format_key(key))))
        return self.db_conn.exists(self._format_key(key))

    def set_value(self, key, value, expiretime=86400):
        key = self._format_key(key)

        #XXX: beaker.container.Value.set_value calls NamespaceManager.set_value
        # however it(until version 1.6.3) never sets expiretime param. Why?

        if (expiretime is None) and (type(value) is tuple):
            try:
                if isinstance(value[1], int) and value[1] > 0:
                    expiretime = value[1]
            except:
                expiretime = 86400
        if expiretime:
            self.db_conn.setex(key, expiretime, pickle.dumps(value))
        else:
            self.db_conn.set(key, pickle.dumps(value))

    def __delitem__(self, key):
        self.db_conn.delete(self._format_key(key))

    def _format_key(self, key):
        return 'beaker:%s:%s' % (self.namespace, key.replace(' ', '\302\267'))

    def do_remove(self):
        self.db_conn.flush()

    def keys(self):
        return self.db_conn.keys('beaker:%s:*' % self.namespace)


class RedisContainer(Container):
    namespace_class = RedisManager
