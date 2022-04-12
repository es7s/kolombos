import unittest

from pytermor import seq

from kolombo.byteio.segment.template import SegmentTemplate


class SegmentTemplateTestCase(unittest.TestCase):
    def test_substitution_auto_processing(self):
        template = SegmentTemplate('@', 'A', seq.GREEN)
        segment = template.substitute(b'123')

        self.assertEqual(segment.data_len, 3)
        self.assertEqual(segment.is_newline, False)
        self.assertEqual(segment.is_consistent, True)
        self.assertEqual(segment.raw, b'123')
        self.assertEqual(segment.processed, '@@@')

    def test_substitution_explicit_processing(self):
        template = SegmentTemplate('@', 'A', seq.GREEN)
        segment = template.substitute(b'123', 'abc')

        self.assertEqual(segment.data_len, 3)
        self.assertEqual(segment.is_newline, False)
        self.assertEqual(segment.is_consistent, True)
        self.assertEqual(segment.raw, b'123')
        self.assertEqual(segment.processed, 'abc')

    def test_substitution_with_different_processed_len(self):
        template = SegmentTemplate('@', 'A', seq.GREEN)
        segment = template.substitute(b'123', 'abcdef')

        self.assertEqual(segment.data_len, 3)
        self.assertEqual(segment.is_newline, False)
        self.assertEqual(segment.is_consistent, False)
        self.assertEqual(segment.raw, b'123')
        self.assertEqual(segment.processed, 'abcdef')

    def test_substitution_with_newline(self):
        template = SegmentTemplate('@', 'A', seq.GREEN)
        segment = template.substitute(b'123', '123\n')

        self.assertEqual(segment.data_len, 3)
        self.assertEqual(segment.is_newline, True)
        self.assertEqual(segment.is_consistent, False)
        self.assertEqual(segment.raw, b'123')
        self.assertEqual(segment.processed, '123\n')


if __name__ == '__main__':
    unittest.main()
