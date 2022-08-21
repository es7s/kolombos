# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
import unittest

from pytermor import IntCodes, SequenceSGR, Seqs

from kolombos.byteio import CharClass
from kolombos.byteio.segment import SegmentBuffer, Segment, StartSequenceRef, StopSequenceRef, OneUseSequenceRef
from kolombos.byteio.template import Template
from kolombos.settings import SettingsManager


class SegmentBufferAttachingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        SettingsManager.init()
        self.buffer = SegmentBuffer()

    def test_attach_segment(self):
        segment = Segment(IntCodes.GREEN, '@', b'123', '123')

        self.buffer.attach(segment)

        self.assertEqual(self.buffer.data_len, 3)
        self.assertEqual(len(self.buffer._segment_chain), 4)
        self.assertIn(StartSequenceRef(IntCodes.GREEN), self.buffer._segment_chain)
        self.assertIn(Segment(IntCodes.GREEN, '@', b'123', '123'), self.buffer._segment_chain)
        self.assertIn(StopSequenceRef(IntCodes.GREEN), self.buffer._segment_chain)
        self.assertIn(OneUseSequenceRef(IntCodes.COLOR_OFF), self.buffer._segment_chain)

    def test_attach_segment_without_formatting(self):
        template = Template(CharClass.PRINTABLE_CHAR, SequenceSGR(), 'E')
        segments = template.substitute(b'123')

        self.buffer.attach(*segments)

        self.assertEqual(self.buffer.data_len, 3)
        self.assertEqual(len(self.buffer._segment_chain), 1)
        self.assertIn(Segment(SequenceSGR(), 'P', b'123', 'EEE'), self.buffer._segment_chain)


class SegmentBufferDetachingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        SettingsManager.init()
        self.buffer = SegmentBuffer()

    def test_detach_whole_segment(self):
        template = Template(CharClass.PRINTABLE_CHAR, Seqs.BG_CYAN, '@')
        segments = template.substitute(b'213')
        self.buffer.attach(*segments)

        processed = self.buffer._detach(3)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 3)
        self.assertIn(StartSequenceRef(Seqs.BG_CYAN), processed)
        self.assertIn(Segment(Seqs.BG_CYAN, 'P', b'213', '@@@'), processed)
        self.assertIn(OneUseSequenceRef(IntCodes.BG_COLOR_OFF), processed)

    def test_detach_partial_segment(self):
        template = Template(CharClass.PRINTABLE_CHAR, Seqs.BOLD, '#')
        segments = template.substitute(b'1234')
        self.buffer.attach(*segments)

        processed = self.buffer._detach(2)

        self.assertEqual(self.buffer.data_len, 2)
        self.assertEqual(len(processed), 3)
        self.assertIn(StartSequenceRef(IntCodes.BOLD), processed)
        self.assertIn(Segment(Seqs.BOLD, 'P', b'12', '##'), processed)
        self.assertIn(OneUseSequenceRef(IntCodes.BOLD_DIM_OFF), processed)

    def test_detach_zero_bytes(self):
        template = Template(CharClass.PRINTABLE_CHAR, Seqs.BOLD, '#')
        segments = template.substitute(b'123')
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
        segments = template.substitute(b'123')
        self.buffer.attach(*segments)

        processed = self.buffer._detach(3)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 1)
        self.assertIn(Segment(SequenceSGR(), 'P', b'123', '...'), processed)

    def test_detach_two_segments(self):
        template1 = Template(CharClass.PRINTABLE_CHAR, Seqs.RED, 'A')
        segments1 = template1.substitute(b'123')
        template2 = Template(CharClass.PRINTABLE_CHAR, Seqs.BG_RED, 'B')
        segments2 = template2.substitute(b'456')
        self.buffer.attach(*segments1)
        self.buffer.attach(*segments2)

        processed = self.buffer._detach(6)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 6)
        self.assertIn(StartSequenceRef(IntCodes.RED), processed)
        self.assertIn(Segment(Seqs.RED, 'P', b'123', 'AAA'), processed)
        self.assertIn(OneUseSequenceRef(IntCodes.COLOR_OFF), processed)
        self.assertIn(StartSequenceRef(IntCodes.BG_RED), processed)
        self.assertIn(Segment(Seqs.BG_RED, 'P', b'456', 'BBB'), processed)
        self.assertIn(OneUseSequenceRef(IntCodes.BG_COLOR_OFF), processed)


if __name__ == '__main__':
    unittest.main()
