import os
import sys
import loghandler
import shutil
import ctypes
import platform

import exceptions
from discord import opus

#Handles logging, checks if various dependencies and files exist, initialises the bot and then attempts to run the bot.

log = loghandler.get_logger(__name__)


def init_opuslib():
    if opus.is_loaded() == False and platform.system() != 'Windows':
        try:
            lib = ctypes.util.find_library('opus')
            opus.load_opus(lib)
        except:
            log.warning(
                f"Could not load the opus library. Are you sure you have an opus library installed?"
            )


def configchecker():
    directorypath = os.path.dirname(__file__)
    defaultconfigpath = os.path.join(directorypath, 'defaultconfig.json')
    configpath = os.path.join(directorypath, 'config.json')

    if os.path.isfile(configpath) == False:
        log.info(
            "Config file does not exist. Attempting to copy the default config file..."
        )
        try:
            shutil.copyfile(defaultconfigpath, configpath)
            log.info('Default config file has been copied successfully.')
        except FileNotFoundError:
            log.critical(
                "Check failed: Could not copy the defaultconfig.json file because it does not exist."
            )
            exit()
    else:
        log.info("Check passed: config file found.")


def sanitychecker():
    log.info("Initialising sanity checks...")
    configchecker()
    init_opuslib()


def exit(message="Press enter to exit...", code=1):
    input(message)
    sys.exit(code)


def main():
    log.info("Starting launcher...")
    sanitychecker()
    log.info("All sanity checks passed!")
    try:
        from esquire import Esquire
        bot = Esquire()
    except exceptions.RestartSignal:
        log.info("Attempting to restart program...")
        main()
    except exceptions.ExitSignal:
        log.info("Program will now exit.")
        exit()


if (__name__ == '__main__'):
    main()