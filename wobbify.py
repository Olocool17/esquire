import io
import logging

log = logging.getLogger(__name__)

punctuationchars = ".?!+-*/\,:;[]()@#$%\'\"`~<>1234567890\n "


def wobbifystring(inputstring):
    wobbifiedstring = ''
    word = ''
    for c in inputstring + ' ':
        if c in punctuationchars:
            if word != '':
                if word.islower():
                    wobbifiedstring += 'wobbe'
                elif len(word) > 1 and word.isupper():
                    wobbifiedstring += 'WOBBE'
                else:
                    wobbifiedstring += 'Wobbe'
            wobbifiedstring += c
            word = ''
        else:
            word += c
    return wobbifiedstring


def wobbifytxt(inputbytes):
    inputstr = inputbytes.decode('UTF-8')
    inputlines = inputstr.splitlines()
    outputlines = [
        wobbifystring(line.replace('\n', '')) for line in inputlines
    ]
    outputstr = '\n'.join(outputlines)
    return io.StringIO(outputstr)