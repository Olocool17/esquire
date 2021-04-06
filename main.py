import os
import logging
import shutil
from esquire import Esquire

log = logging.getLogger(__name__)


def configchecker():
    directorypath = os.path.dirname(__file__)
    defaultconfigpath = os.path.join(directorypath, 'defaultconfig.json')
    configpath = os.path.join(directorypath, 'config.json')

    if os.path.isfile(configpath):
        return True
    else:
        log.warning(
            'Config file does not exist. Attempting to copy the default config file...'
        )
        try:
            shutil.copyfile(defaultconfigpath, configpath)
            log.info('Default config file has been copied successfully.')
            return True
        except FileNotFoundError:
            log.error(
                'Could not copy the defaultconfig.json file because it does not exist.'
            )
            return False


def main():
    if configchecker():
        bot = Esquire()


if (__name__ == '__main__'):
    main()