import unittest

from transfer_serial import lrc


class TestLRC(unittest.TestCase):
    def test_lrc(self):
        # テストケース1: ASCII文字列
        data = b"Hello, World!".decode()
        expected = "2D"
        actual = lrc(data)
        self.assertEqual(actual, expected)

        # テストケース2: バイナリデータ
        data = b"\x01\x02\x03\x04\x05"
        expected = 0x05
        actual = lrc(data)
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
