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
        self.serial_communication = SerialCommunication(transport)

    def data_received(self, data):
        print("data received", repr(data))
        self.pause_reading()

    def connection_lost(self, exc):
        self.transport.loop.stop()

    def pause_writing(self):
        print("pause writing")
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print("resume writing")

    def pause_reading(self):
        self.transport.pause_reading()

    def resume_reading(self):
        self.transport.resume_reading()


class SerialCommunication:
    def __init__(self, transport) -> None:
        self.transport = transport
        logging.info("port opend", transport)

    async def send_string_as_byte(self, writestr: str):
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.transport.write, writestr.encode())
            logging.info("Send", self.transport)
            return True
        except Exception as e:
            logging.error(f"Failed to send data: {e}")
            return False

    async def resume_reading(self):
        bytelist = []
        try:
            if self.transport.serial.in_waiting > 0:
                for i in range(self.transport.serial.in_waiting):
                    bytelist.append(self.transport.serial.read())
                # print(type(bytelist[1]))
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
        byteData: list,
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
                if byte == startText:
                    processing = True
                    continue
                elif byte == endText:
                    break
                if processing:
                    print(type(byte), byte)
                    checkValue ^= ord(byte)
            return format(checkValue, "02x")
        except Exception as e:
            logging.error(f"Fail parity check: {e}")
            return False


bytelist = [b"\x02", b"1", b"c", b"*", b"\x03"]


async def readerAndWriter():
    # logging.basicConfig(level=logging.INFO)

    # serial port setting
    port = "COM3"
    baudrate = 9600

    transport, protocol = await serial_asyncio.create_serial_connection(
        loop, AsyncSerialCommunicator, port, baudrate=baudrate
    )

    while True:
        await asyncio.sleep(0.3)
        await protocol.serial_communication.send_string_as_byte("Hello World!")

        test = await protocol.serial_communication.resume_reading()
        print(type(test[1]), test[1])
        test1 = await DataParser.parity_check(test, startText=None, endText=None)
        print(test1)


loop = asyncio.get_event_loop()
loop.run_until_complete(readerAndWriter())
loop.close()
