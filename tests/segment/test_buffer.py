import unittest

from pytermor import seq

from kolombo.byteio.segment.buffer import SegmentBuffer
from kolombo.byteio.segment.segment import Segment
from kolombo.byteio.segment.sequence_ref import StartSequenceRef, StopSequenceRef, OneUseSequenceRef
from kolombo.byteio.segment.template import SegmentTemplate


class SegmentBufferAttachingTestCase(unittest.TestCase):
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


class SegmentBufferDetachingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.buffer = SegmentBuffer()

    def test_detach_whole_segment(self):
        template = SegmentTemplate('@', 'A', seq.BG_CYAN)
        segment = template.substitute(b'123', '123')
        self.buffer.attach(segment)

        processed = self.buffer._detach(3)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 3)
        self.assertIn(StartSequenceRef(seq.BG_CYAN), processed)
        self.assertIn(Segment(template, b'123', '123'), processed)
        self.assertIn(OneUseSequenceRef(seq.BG_COLOR_OFF), processed)

    def test_detach_partial_segment(self):
        template = SegmentTemplate('@', 'A', seq.BOLD)
        segment = template.substitute(b'1234', '1234')
        self.buffer.attach(segment)

        processed = self.buffer._detach(2)

        self.assertEqual(self.buffer.data_len, 2)
        self.assertEqual(len(processed), 3)
        self.assertIn(StartSequenceRef(seq.BOLD), processed)
        self.assertIn(Segment(template, b'12', '12'), processed)
        self.assertIn(OneUseSequenceRef(seq.BOLD_DIM_OFF), processed)

    def test_detach_zero_bytes(self):
        template = SegmentTemplate('@', 'A', seq.BOLD)
        segment = template.substitute(b'123', '123')
        self.buffer.attach(segment)

        processed = self.buffer._detach(0)

        self.assertEqual(self.buffer.data_len, 3)
        self.assertEqual(len(processed), 0)

    def test_detach_empty(self):
        processed = self.buffer._detach(0)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 0)

    def test_detach_segment_without_formatting(self):
        template = SegmentTemplate('-', 'E')
        segment = template.substitute(b'123', '123')
        self.buffer.attach(segment)

        processed = self.buffer._detach(3)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 1)
        self.assertIn(Segment(template, b'123', '123'), processed)

    def test_detach_two_segments(self):
        template1 = SegmentTemplate('@', 'A', seq.RED)
        segment1 = template1.substitute(b'123', '123')
        template2 = SegmentTemplate('@', 'B', seq.BG_RED)
        segment2 = template2.substitute(b'456', '456')
        self.buffer.attach(segment1)
        self.buffer.attach(segment2)

        processed = self.buffer._detach(6)

        self.assertEqual(self.buffer.data_len, 0)
        self.assertEqual(len(processed), 6)
        self.assertIn(StartSequenceRef(seq.RED), processed)
        self.assertIn(Segment(template1, b'123', '123'), processed)
        self.assertIn(OneUseSequenceRef(seq.COLOR_OFF), processed)
        self.assertIn(StartSequenceRef(seq.BG_RED), processed)
        self.assertIn(Segment(template2, b'456', '456'), processed)
        self.assertIn(OneUseSequenceRef(seq.BG_COLOR_OFF), processed)


if __name__ == '__main__':
    unittest.main()
