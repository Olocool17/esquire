import json
import loghandler
import logging

log = loghandler.get_logger(__name__)


class JsonHandler:
    def __init__(self, jsonfile):
        self.jsonfile = jsonfile
        self.data = self.parse()

    def parse(self):
        with open(self.jsonfile, 'r') as infile:
            try:
                parsed = json.load(infile)
            except:
                log.error(f'Error parsing {self.jsonfile}')
                parsed = {}
            return parsed

    def get(self, key, default=None):
        try:
            if isinstance(key, list):
                value = self.data
                for k in key:
                    value = value[k]
            else:
                value = self.data[key]
        except KeyError:
            value = default
            if value == None:
                log.error(
                    f"Could not retrieve value for key \'{key}\' from JSON. None returned."
                )
            else:
                log.warning(
                    f"Could not retrieve value for key \'{key}\' from JSON. Default returned."
                )

        return value

    def update(self, item, value, rootkey=None):
        root = self.data
        if rootkey != None:
            rootkey = [rootkey] if not isinstance(rootkey, list) else rootkey
            #Create dictionary entries if they don't exist yet
            for k in rootkey:
                try:
                    root = root[k]
                except KeyError:
                    root.update({k: {}})
                    root = root[k]
        try:
            root.update({item: value})
        except:
            log.error(
                f"Could not update the root \'{root}\' with the item/value \'{item}/{value}\'"
            )

    def write(self):
        with open(self.jsonfile, 'w') as outfile:
            try:
                json.dump(self.data, outfile, indent='\t')
            except:
                log.error(f"Error writing to {self.jsonfile}")


class QuotesHandler(JsonHandler):
    def get_all_from_guild(self, guild):
        pass