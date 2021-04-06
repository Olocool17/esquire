import os
import sys
import logging
import shutil
from esquire import Esquire

log = logging.getLogger(__name__)

#Handles logging, checks if various dependencies and files exist, initialises the bot and then attempts to run the bot.


def configchecker():
    directorypath = os.path.dirname(__file__)
    defaultconfigpath = os.path.join(directorypath, 'defaultconfig.json')
    configpath = os.path.join(directorypath, 'config.json')

    if os.path.isfile(configpath) == False:
        log.info(
            'Config file does not exist. Attempting to copy the default config file...'
        )
        try:
            shutil.copyfile(defaultconfigpath, configpath)
            log.info('Default config file has been copied successfully.')
        except FileNotFoundError:
            log.critical(
                'Could not copy the defaultconfig.json file because it does not exist.'
            )
            exit()


def sanitychecker():
    log.info("Initialising sanity checks...")

    configchecker()


def exit(message="Press enter to exit...", code=1):
    input(message)
    sys.exit(code)


def main():
    sanitychecker()

    bot = Esquire()
    bot.initialise()


if (__name__ == '__main__'):
    main()