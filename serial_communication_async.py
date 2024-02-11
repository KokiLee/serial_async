import asyncio
import configparser
import logging
import os
import threading
import tkinter as tk

import serial_asyncio


# Ser class modify
class AsyncSerialCommunicator(asyncio.Protocol):
    # called by asyncio when establishment a connection.
    # Save transport object to instance variable and Make instance of SrialCommunication class.
    # "Request to send" to disable.
    def connection_made(self, transport):
        self.transport = transport
        print("port opened", transport)
        transport.serial.rts = False
        self.serial_communication = SerialCommunication(transport)

    # data-received-class is for data receive. data-received-class called by asyncio.
    # This method displays receive data. data reading paused.
    def data_received(self, data):
        print("data received", repr(data))
        self.pause_reading()

    # called by asyncio when connection lost. "exc" parameter is an exception object.
    # if the connection is correctly closed,no exception will occur.
    def connection_lost(self, exc):
        self.transport.loop.stop()

    # if writing buffer is upper limmit,called by asyncio.
    def pause_writing(self):
        print("pause writing")
        print(self.transport.get_write_buffer_size())

    # Called by asyncio when writing buffer is the acceptable range.
    # This method is used to resume writing.
    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print("resume writing")

    # This method is used to pause data reading.
    # If data processing data takes a long time, or buffer overflow prevents reading, reading may be paused.
    def pause_reading(self):
        self.transport.pause_reading()

    # This method resumes reading paused data.
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

    async def read_serial_data_as_byte_list(self):
        bytelist = []
        try:
            if self.transport.serial.in_waiting > 0:
                for i in range(self.transport.serial.in_waiting):
                    bytelist.append(self.transport.serial.read())
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

    def close_port(self):
        if self.transport:
            self.transport.close()
            logging.info("Serial port closed")


class DataParser:
    @staticmethod
    async def byte_to_ascii(
        bytelist: bytes,
        dec: str = "utf-8",
        startText: bytes = b"\x02",
        endText: bytes = b"\x03",
    ):
        """文字コードが違う場合は引数 dec で指定してください。デフォルトは utf-8"""
        decli = []
        try:
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


async def readerAndWriter(loop):
    # logging.basicConfig(level=logging.INFO)

    # serial port setting
    port = "COM3"
    baudrate = 9600

    transport, protocol = await serial_asyncio.create_serial_connection(
        loop, AsyncSerialCommunicator, port, baudrate=baudrate
    )
    try:
        while True:
            await asyncio.sleep(0.3)
            await protocol.serial_communication.send_string_as_byte(
                # chr(0x02)
                "Yesterday,I had an accident.\n I was cleaning my room.\nI used the vacuum cleaner.\nI pulled the chair and cleaned under it.\nThen I pulled the desk and cleaned under it.\nI wanted to cleaned under the bed next.\n"
            )

            test = await protocol.serial_communication.read_serial_data_as_byte_list()
            # test = await protocol.serial_communication.read_line_as_bytes()
            print(type(test[1]), test[1])
            test1 = await DataParser.parity_check(
                test[1], startText=None, endText=None, initialValue=0
            )
            print(test1)
            test2 = await DataParser.byte_to_ascii(test[1])
            print(test2)

    except asyncio.CancelledError:
        print("Task was cancelled")

    finally:
        protocol.serial_communication.close_port()


async def main(loop):
    task = loop.create_task(readerAndWriter(loop))
    try:
        await task

    except asyncio.CancelledError:
        print("Task was cancelled")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(readerAndWriter(loop))

    except KeyboardInterrupt:
        # Ctrl + c Program was stoped
        print("Program terminated by user")
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.stop()

    finally:
        loop.close()
