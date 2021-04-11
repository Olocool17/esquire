import json
import logging

log = logging.getLogger(__name__)


class JsonHandler:
    def __init__(self, jsonfile):
        self.jsonfile = jsonfile
        self.data = self.parse()

    def parse(self):
        with open(self.jsonfile, 'r') as infile:
            try:
                parsed = json.load(infile)
            except Exception:
                log.error(f'Error parsing {self.jsonfile}')
                parsed = {}
            return parsed

    def get(self, key, default=None):
        try:
            if isinstance(key, list):
                value = self.data[key[0]]
                for k in key[1:]:
                    value = value[k]
            else:
                value = self.data[key]
        except KeyError:
            value = default
            if value == None:
                log.error(
                    f'Could not retrieve value for key \'{key}\' from JSON. None returned.'
                )
            else:
                log.warning(
                    f'Could not retrieve value for key \'{key}\' from JSON. Default returned.'
                )

        return value


class QuotesHandler(JsonHandler):
    def get_all_from_guild(self, guild):
        pass