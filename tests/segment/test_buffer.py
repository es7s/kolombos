import unittest

from pytermor import seq, autof

from kolombo.byteio.segment.buffer import SegmentBuffer
from kolombo.byteio.segment.segment import Segment
from kolombo.byteio.segment.sequence_ref import StartSequenceRef, StopSequenceRef, OneUseSequenceRef
from kolombo.byteio.segment.template import SegmentTemplate


class SegmentBufferTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.buffer = SegmentBuffer()

    def test_attach_segment(self):
        template = SegmentTemplate('@', 'A', seq.GREEN)
        segment = template.substitute(b'123', '123')
        self.buffer.attach(segment)

        self.assertEqual(self.buffer.data_len, 3)
        self.assertEqual(len(self.buffer._segment_chain), 4)
        self.assertIn(StartSequenceRef(seq.GREEN), self.buffer._segment_chain)
        self.assertIn(Segment(template, b'123', '123'), self.buffer._segment_chain)
        self.assertIn(StopSequenceRef(seq.GREEN), self.buffer._segment_chain)
        self.assertIn(OneUseSequenceRef(seq.COLOR_OFF), self.buffer._segment_chain)

    def test_attach_segment_without_formatting(self):
        template = SegmentTemplate('-', 'E')
        segment = template.substitute(b'123', '123')
        self.buffer.attach(segment)

        self.assertEqual(self.buffer.data_len, 3)
        self.assertEqual(len(self.buffer._segment_chain), 1)
        self.assertIn(Segment(template, b'123', '123'), self.buffer._segment_chain)
