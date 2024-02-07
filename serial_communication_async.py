import asyncio
import configparser
import logging
import os
import tkinter as tk

import serial_asyncio


# Ser class modify
class AsyncSerialCommunicator(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        print("port opened", transport)
        transport.serial.rts = False
        self.config = SerialConfig(transport)
        self.communication = SerialCommunication(transport)
        transport.write(b"Hello World! abcdefghijklmn\n")

    def data_received(self, data):
        print("data received", repr(data))
        if b"\n" in data:
            self.transport.close()

    def connection_lost(self, exc):
        self.transport.loop.stop()

    def pause_writing(self):
        print("pause writing")
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print("resume writing")


class SerialConfig:
    def __init__(self, transport) -> None:
        self.transport = transport

    def port_open(self):
        logging.info("Port is successfully opend")

    def port_close(self):
        try:
            self.transport.close()
            return True
        except Exception as e:
            logging.error(f"Failed to close port: {e}")
        return False


class SerialCommunication:
    def __init__(self, transport) -> None:
        self.transport = transport

    async def send_string_as_byte(self, writestr: str):
        try:
            self.transport.write(writestr.encode())
            return "Send Start"
        except Exception as e:
            logging.error(f"Failed to send data: {e}")
            return False

    async def read_available_bytes(self):
        bytelist = []
        try:
            if self.transport.serial.in_wating > 0:
                for i in range(self.transport.serial.in_waiting):
                    bytelist.append(self.transport.serial.read())
                print(type(bytelist[1]))
                return "Read Start\n", bytelist
            else:
                return "Read Fail\n", bytelist
        except Exception as e:
            logging.error(f"Failed to receive data: {e}")
            return "Read Faile\n", bytelist

    async def read_line_as_bytes(self):
        bytelist = []
        try:
            byteall = self.transport.serial.readline()
            print(byteall)
            for i in byteall:
                bytelist.append(i.to_bytes(1, "big"))
            return "Read Start\n", bytelist
        except Exception as e:
            logging.error(f"Failed to receive data: {e}")
            return "Read Fail\n", bytelist

    def data_received(self, data):
        # 受信データを処理する
        try:
            decoded_data = data.decode("utf-8")  # 例: データをUTF-8でデコード
            print(f"Received data: {decoded_data}")
            # ここで受信データに基づいてさらなる処理を行う
        except Exception as e:
            logging.error(f"Failed to process received data: {e}")


class DataParser:
    @staticmethod
    async def byte_to_ascii(
        bytelist: list,
        dec: str = "utf-8",
        startText: bytes = b"\x02",
        endText: bytes = b"\x03",
    ):
        """文字コードが違う場合は引数 dec で指定してください。デフォルトは utf-8"""
        decli = []
        try:
            if startText == bytelist[0]:
                for i in bytelist:
                    if i == endText:
                        break
                    decli.append(i.decode(dec))
                return "".join(decli)
        except Exception as e:
            logging.error(f"No data: {e}")

    @staticmethod
    async def parity_check(
        byteData: bytes,
        startText: bytes = b"\x02",
        endText: bytes = b"*",
        initialValue: int = 0,
    ):
        """startText から endText の間でチェックコードを生成します。initialValue は初期値
        startText と endText でデータの開始と終了を指定します。
        """
        try:
            processing = True if startText is None else False
            checkValue = initialValue

            for byte in byteData:
                if startText == endText:
                    return ""
                if byte == startText:
                    processing = True
                    continue
                elif byte == endText:
                    break
                if processing:
                    checkValue ^= ord(byte)
            return format(checkValue, "02x")
        except Exception as e:
            logging.error(f"Fail parity check: {e}")
            return False


bytelist = [b"\x02", b"1", b"c", b"*", b"\x03"]


# serial port setting
port = "COM3"
baudrate = 9600

loop = asyncio.get_event_loop()
coro = serial_asyncio.create_serial_connection(
    loop, AsyncSerialCommunicator, "COM3", baudrate=baudrate
)
transport, protocol = loop.run_until_complete(coro)
loop.run_forever()
loop.close()
# result1 = await DataParser.parity_check(data)
# print(type(result1), result1)


# main関数を実行
