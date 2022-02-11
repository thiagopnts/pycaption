from .base import (
    BaseReader, BaseWriter, CaptionSet, Caption, CaptionNode)
from .exceptions import CaptionReadNoCaptions

import re

class SRTReader(BaseReader):
    def detect(self, content):
        lines = content.splitlines()
        if len(lines) < 2:
            return False
        if self._isdigit(lines[0]) and u'-->' in lines[1]:
            return True
        return False

    def read(self, content, lang=u'en-US'):
        if type(content) != unicode:
            raise RuntimeError('The content is not a unicode string.')

        caption_set = CaptionSet()
        lines = content.splitlines()
        start_line = 0
        captions = []

        while start_line < len(lines):
            if not self._isdigit(lines[start_line]):
                break

            caption = Caption()

            end_line = self._find_text_line(start_line, lines)

            # Stupid hacks for malformed files
            timing = re.match('^([0-9]{1,}:[0-9]{1,}:[0-9]{1,},[0-9]{1,}) --> ([0-9]{1,}:[0-9]{1,}:[0-9]{1,},[0-9]{1,})', lines[start_line + 1])
            if timing == None:
                timing = lines[start_line + 1].split(u'-->')
                if len(timing) < 2:
                    raise CaptionReadNoCaptions("Malformed file.")
                else:
                    caption.start = self._srttomicro(timing[0].strip(u' \r\n'))
                    caption.end = self._srttomicro(timing[1].strip(u' \r\n'))
            else:
                caption.start = self._srttomicro(timing.group(1).strip(u' \r\n'))
                caption.end = self._srttomicro(timing.group(2).strip(u' \r\n'))

            for line in lines[start_line + 2:end_line - 1]:
                line = re.sub(re.compile(u"<font color=\"#[0-9a-f]{6}\">", re.I | re.U), "", line, re.I | re.U)
                line = re.sub(re.compile(u"</font>", re.I | re.U), "", line, re.I | re.U)
                # skip extra blank lines
                if not caption.nodes or line != u'':
                    caption.nodes.append(CaptionNode.create_text(line))
                    caption.nodes.append(CaptionNode.create_break())

            # remove last line break from end of caption list
            if len(caption.nodes):
                caption.nodes.pop()
                captions.append(caption)

            start_line = end_line

        caption_set.set_captions(lang, captions)

        if caption_set.is_empty():
            raise CaptionReadNoCaptions(u"empty caption file")

        return caption_set

    def _isdigit(self, line):
        matchset = re.match('[0-9]{1,}', line)
        return matchset != None

    def _srttomicro(self, stamp):
        timesplit = stamp.split(u':')
        if u',' not in timesplit[2]:
            timesplit[2] = timesplit[2] + u',000'
        secsplit = timesplit[2].split(u',')
        microseconds = (int(timesplit[0]) * 3600000000 +
                        int(timesplit[1]) * 60000000 +
                        int(secsplit[0]) * 1000000 +
                        int(secsplit[1]) * 1000)

        return microseconds

    def _find_text_line(self, start_line, lines):
        end_line = start_line

        found = False
        while end_line < len(lines):
            if lines[end_line].strip() == u"":
                found = True
            elif found is True:
                end_line -= 1
                break
            end_line += 1

        return end_line + 1


class SRTWriter(BaseWriter):
    def write(self, captions):
        srt_captions = []

        for lang in captions.get_languages():
            srt_captions.append(
                self._recreate_lang(captions.get_captions(lang))
            )

        caption_content = u'MULTI-LANGUAGE SRT\n'.join(srt_captions)
        return caption_content

    def _recreate_lang(self, captions):
        srt = []
        count = 1

        for caption in captions:
            srt.append(u'%s\n' % count)

            start = caption.format_start(msec_separator=u',')
            end = caption.format_end(msec_separator=u',')
            timestamp = u'%s --> %s\n' % (start[:12], end[:12])

            srt.append(timestamp.replace(u'.', u','))

            new_content = u''
            for node in caption.nodes:
                new_content = self._recreate_line(new_content, node)

            # Eliminate excessive line breaks
            new_content = new_content.strip()
            while u'\n\n' in new_content:
                new_content = new_content.replace(u'\n\n', u'\n')

            srt.append(u"%s%s" % (new_content, u'\n\n'))
            count += 1

        return ''.join(srt)[:-1]  # remove unwanted newline at end of file

    def _recreate_line(self, srt, line):
        if line.type == CaptionNode.TEXT:
            return srt + u'%s ' % line.content
        elif line.type == CaptionNode.BREAK:
            return srt + u'\n'
        else:
            return srt
