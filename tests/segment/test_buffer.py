# -----------------------------------------------------------------------------
# es7s/kolombo [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
import unittest

from pytermor import sgr, SequenceSGR, seq

from kolombo.byteio import CharClass
from kolombo.byteio.segment import SegmentBuffer, Segment, StartSequenceRef, StopSequenceRef, OneUseSequenceRef
from kolombo.byteio.template import Template
from kolombo.settings import SettingsManager


class SegmentBufferAttachingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        SettingsManager.init()
        self.buffer = SegmentBuffer()

    def test_attach_segment(self):
        segment = Segment(sgr.GREEN, '@', b'123', '123')

        self.buffer.attach(segment)

        self.assertEqual(self.buffer.data_len, 3)
        self.assertEqual(len(self.buffer._segment_chain), 4)
        self.assertIn(StartSequenceRef(sgr.GREEN), self.buffer._segment_chain)
        self.assertIn(Segment(sgr.GREEN, '@', b'123', '123'), self.buffer._segment_chain)
        self.assertIn(StopSequenceRef(sgr.GREEN), self.buffer._segment_chain)
        self.assertIn(OneUseSequenceRef(sgr.COLOR_OFF), self.buffer._segment_chain)

    def test_attach_segment_without_formatting(self):
        template = Template(CharClass.PRINTABLE_CHAR, SequenceSGR(), 'E')
        segments = template.substitute(None, b'123')

        self.buffer.attach(*segments)

        self.assertEqual(self.buffer.data_len, 3)
        self.assertEqual(len(self.buffer._segment_chain), 1)
        self.assertIn(Segment(SequenceSGR(), 'P', b'123', 'EEE'), self.buffer._segment_chain)


class SegmentBufferDetachingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        SettingsManager.init()
        self.buffer = SegmentBuffer()

    def test_detach_whole_segment(self):
        template = Template(CharClass.PRINTABLE_CHAR, seq.BG_CYAN, '@')
        segments = template.substitute(None, b'213')
        self.buffer.attach(*segments)

        processed = self.buffer._detach(3)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 3)
        self.assertIn(StartSequenceRef(seq.BG_CYAN), processed)
        self.assertIn(Segment(seq.BG_CYAN, 'P', b'213', '@@@'), processed)
        self.assertIn(OneUseSequenceRef(sgr.BG_COLOR_OFF), processed)

    def test_detach_partial_segment(self):
        template = Template(CharClass.PRINTABLE_CHAR, seq.BOLD, '#')
        segments = template.substitute(None, b'1234')
        self.buffer.attach(*segments)

        processed = self.buffer._detach(2)

        self.assertEqual(self.buffer.data_len, 2)
        self.assertEqual(len(processed), 3)
        self.assertIn(StartSequenceRef(sgr.BOLD), processed)
        self.assertIn(Segment(seq.BOLD, 'P', b'12', '##'), processed)
        self.assertIn(OneUseSequenceRef(sgr.BOLD_DIM_OFF), processed)

    def test_detach_zero_bytes(self):
        template = Template(CharClass.PRINTABLE_CHAR, seq.BOLD, '#')
        segments = template.substitute(None, b'123')
        self.buffer.attach(*segments)

        processed = self.buffer._detach(0)

        self.assertEqual(self.buffer.data_len, 3)
        self.assertEqual(len(processed), 0)

    def test_detach_empty(self):
        processed = self.buffer._detach(0)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 0)

    def test_detach_segment_without_formatting(self):
        template = Template(CharClass.PRINTABLE_CHAR, SequenceSGR(), '.')
        segments = template.substitute(None, b'123')
        self.buffer.attach(*segments)

        processed = self.buffer._detach(3)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 1)
        self.assertIn(Segment(SequenceSGR(), 'P', b'123', '...'), processed)

    def test_detach_two_segments(self):
        template1 = Template(CharClass.PRINTABLE_CHAR, seq.RED, 'A')
        segments1 = template1.substitute(None, b'123')
        template2 = Template(CharClass.PRINTABLE_CHAR, seq.BG_RED, 'B')
        segments2 = template2.substitute(None, b'456')
        self.buffer.attach(*segments1)
        self.buffer.attach(*segments2)

        processed = self.buffer._detach(6)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 6)
        self.assertIn(StartSequenceRef(sgr.RED), processed)
        self.assertIn(Segment(seq.RED, 'P', b'123', 'AAA'), processed)
        self.assertIn(OneUseSequenceRef(sgr.COLOR_OFF), processed)
        self.assertIn(StartSequenceRef(sgr.BG_RED), processed)
        self.assertIn(Segment(seq.BG_RED, 'P', b'456', 'BBB'), processed)
        self.assertIn(OneUseSequenceRef(sgr.BG_COLOR_OFF), processed)


if __name__ == '__main__':
    unittest.main()
