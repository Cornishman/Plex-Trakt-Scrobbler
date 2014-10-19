import hashlib
import logging
import struct

log = logging.getLogger(__name__)


class Packer(object):
    key_code = {
        'thetvdb'    : 1,
        'imdb'       : 2,
        'tvrage'     : 3,
        'themoviedb' : 4
    }

    @classmethod
    def pack(cls, obj, include=None):
        p_name = obj.__class__.__name__.lower()
        p_method = getattr(cls, 'pack_' + p_name, None)

        if include is not None and type(include) is not list:
            include = [include]

        if p_method:
            return p_method(obj, include)

        raise Exception("Unknown object specified - name: %r" % p_name)

    @classmethod
    def pack_movie(cls, movie, include):
        result = {
            '_': 'show',

            'k': [
                (cls.to_key_code(key), value)
                for (key, value) in movie.keys
            ],

            't': movie.title,
            'y': struct.pack('H', movie.year),
        }

        # Collected
        if not include or 'c' in include:
            # ['c'] = (is_collected, timestamp)
            result['c'] = struct.pack('?I', movie.is_collected, 0)

        # Ratings
        if not include or 'r' in include:
            # ['r'] = (rating, timestamp)
            result['r'] = struct.pack('fI', movie.rating.advanced, movie.rating.timestamp) if movie.rating else None

        # Watched
        if not include or 'w' in include:
            # ['w'] = (is_watched)
            result['w'] = struct.pack('?', movie.is_watched)

        # Calculate item hash
        result['@'] = cls.hash(result)

        return result

    @classmethod
    def pack_show(cls, show, include):
        result = {
            '_': 'show',

            'k': [
                (cls.to_key_code(key), value)
                for (key, value) in show.keys
            ],

            't': show.title,
            'y': struct.pack('H', show.year),

            'z': {}
        }

        # Collected
        if not include or 'c' in include:
            # ['z']['c'] = (se, ep, timestamp)
            result['z']['c'] = [
                struct.pack('HHI', se, ep, 0)
                for (se, ep), episode in show.episodes.items()
                if episode.is_collected
            ]

        # Ratings
        if not include or 'r' in include:
            # ['r'] = (rating, timestamp)
            result['r'] = struct.pack('fI', show.rating.advanced, show.rating.timestamp) if show.rating else None

            # ['z']['r'] = (se, ep, rating, timestamp)
            result['z']['r'] = [
                struct.pack('HHfI', se, ep, episode.rating.advanced, episode.rating.timestamp)
                for (se, ep), episode in show.episodes.items()
                if episode.rating is not None
            ]

        # Watched
        if not include or 'w' in include:
            result['z']['w'] = [
                struct.pack('HH', se, ep)
                for (se, ep), episode in show.episodes.items()
                if episode.is_watched
            ]

        # Calculate item hash
        result['@'] = cls.hash(result)

        return result

    @classmethod
    def to_key_code(cls, key):
        result = cls.key_code.get(key)

        if result is None:
            log.warn('Unable to find key code for "%s"', key)

        return result

    @staticmethod
    def hash(item):
        # TODO check performance of this
        m = hashlib.md5()
        m.update(repr(item))

        return m.hexdigest()