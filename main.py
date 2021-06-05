import os
import sys
import loghandler
import shutil

import exceptions
from discord import opus
from esquire import Esquire

#Handles logging, checks if various dependencies and files exist, initialises the bot and then attempts to run the bot.

log = loghandler.get_logger(__name__)

OPUS_LIBS = [
    'libopus-0.x64.dll', 'libopus-0.x86.dll', 'libopus-0.dll', 'libopus.so.0',
    'libopus.0.dylib'
]


def init_opuslib():
    if opus.is_loaded() == False:
        for opuslib in OPUS_LIBS:
            try:
                opus.load_opus(opuslib)
            except:
                log.warning(f"Could not load the opus library \'{opuslib} \'")


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


def exit(message="Press enter to exit...", code=1):
    input(message)
    sys.exit(code)


def main():
    log.info("Starting launcher...")
    sanitychecker()
    log.info("All sanity checks passed!")
    init_opuslib()
    try:
        bot = Esquire()

    except SyntaxError:
        log.exception(
            "CRINGE ALERT! CRINGY SYNTAX ERROR ENCOUNTERED! SHAME! SHAME! SHAME!"
        )
    except exceptions.RestartSignal:
        log.info("Attempting restart...")
        main()
    except exceptions.ExitSignal:
        log.info("Program will now exit.")
        exit()


if (__name__ == '__main__'):
    main()