import unittest

from serial_communication_async import AsyncSerialCommunicator


# need to modify
class TestTransferSerialAsync(unittest.TestCase):
    def test_data_received(self):
        # Transfer_serial_async インスタンスを作成
        transfer = AsyncSerialCommunicator()

        # テストデータ
        test_data = b"Hello, World!"

        # data_received メソッドを呼び出す
        transfer.data_received(test_data)

        # データが正しく追加されたことを確認
        self.assertEqual(transfer.data[0], test_data)


if __name__ == "__main__":
    unittest.main()
