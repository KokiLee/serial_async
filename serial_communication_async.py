import asyncio
import configparser
import logging
import math
import os
import threading
import time
import tkinter as tk

import chardet
import matplotlib.pyplot as plt
import numpy as np
import serial_asyncio
from matplotlib.animation import FuncAnimation

# from vpython import box, rate, vector


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
                return bytelist
        except Exception as e:
            logging.error(f"Failed to receive data: {e}")
            return False

    async def read_line_as_bytes(self):
        bytelist = []
        try:
            byteall = self.transport.serial.readline()
            for i in byteall:
                bytelist.append(i.to_bytes(1, "big"))
            return bytelist
        except Exception as e:
            logging.error(f"Failed to receive data: {e}")
            return bytelist

    def close_port(self):
        if self.transport:
            self.transport.close()
            logging.info("Serial port closed")


class DataParser:
    @staticmethod
    async def byte_to_ascii(
        byteData: bytes,
        dec: str = "utf-8",
        startText: bytes = b"\x02",
        endText: bytes = b"\x03",
    ):
        """文字コードが違う場合は引数 dec で指定してください。デフォルトは utf-8"""
        decodelist = []
        if byteData is not None:
            try:
                for i in byteData:
                    if ascii_control_codes.get(i) is not None:
                        decodelist.append(ascii_control_codes.get(i))
                    if i == endText:
                        break
                    decodelist.append(i.decode(dec))
                return "".join(decodelist)
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
        if byteData is not None:
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

    @staticmethod
    async def adjust_angle_async(current_angle, previous_angle):
        """
        Corrected overflow and underflow when angular difference exceeding 180 degree
        :return: corrected angle
        """
        if previous_angle != 0:
            angle_diff = current_angle - previous_angle
            if angle_diff > 180:
                current_angle -= 360
            elif angle_diff < -180:
                current_angle += 360
        return current_angle

    @staticmethod
    async def witmotion_standard_protocol_angular(data):
        previous_roll = 0
        previous_pitch = 0
        previous_yaw = 0
        roll = None
        pitch = None
        yaw = None
        try:
            for i in range(len(data) - 1):
                if data[i] == b"\x55" and data[i + 1] == b"\x53":

                    roll_H = int.from_bytes(
                        data[i + 3], byteorder="little", signed=True
                    )
                    roll_L = int.from_bytes(
                        data[i + 2], byteorder="little", signed=True
                    )
                    # ((roll_H << 8) + roll_L) = Current angle
                    roll = ((roll_H << 8) + roll_L) / 32768.0 * 180

                    pitch_L = int.from_bytes(
                        data[i + 4], byteorder="little", signed=True
                    )
                    pitch_H = int.from_bytes(
                        data[i + 5], byteorder="little", signed=True
                    )

                    pitch = ((pitch_H << 8) + pitch_L) / 32768.0 * 180

                    yaw_H = int.from_bytes(
                        data[i + 7], byteorder="little", signed=True
                    )
                    yaw_L = int.from_bytes(
                        data[i + 6], byteorder="little", signed=True
                    )

                    yaw = ((yaw_H << 8) + yaw_L) / 32768.0 * 180

                    # Implemented a solution to correct overflow and underflow in sensor data processing.
                    roll = await DataParser.adjust_angle_async(roll, previous_roll)
                    pitch = await DataParser.adjust_angle_async(pitch, previous_pitch)
                    yaw = await DataParser.adjust_angle_async(yaw, previous_yaw)

            return roll, pitch, yaw
        except:
            pass


ascii_control_codes = {
    b"\x00": "NUL (Null char)",
    b"\x01": "SOH (Start of Heading)",
    b"\x02": "STX (Start of Text)",
    b"\x03": "ETX (End of Text)",
    b"\x04": "EOT (End of Transmission)",
    b"\x05": "ENQ (Enquiry)",
    b"\x06": "ACK (Acknowledge)",
    b"\x07": "BEL (Bell)",
    b"\x08": "BS (Backspace)",
    b"\x09": "HT (Horizontal Tab)",
    b"\x0A": "LF (Line Feed)",
    b"\x0B": "VT (Vertical Tab)",
    b"\x0C": "FF (Form Feed)",
    b"\x0D": "CR (Carriage Return)",
    b"\x0E": "SO (Shift Out)",
    b"\x0F": "SI (Shift In)",
    b"\x10": "DLE (Data Link Escape)",
    b"\x11": "DC1 (Device Control 1)",
    b"\x12": "DC2 (Device Control 2)",
    b"\x13": "DC3 (Device Control 3)",
    b"\x14": "DC4 (Device Control 4)",
    b"\x15": "NAK (Negative Acknowledge)",
    b"\x16": "SYN (Synchronous Idle)",
    b"\x17": "ETB (End of Transmission Block)",
    b"\x18": "CAN (Cancel)",
    b"\x19": "EM (End of Medium)",
    b"\x1A": "SUB (Substitute)",
    b"\x1B": "ESC (Escape)",
    b"\x1C": "FS (File Separator)",
    b"\x1D": "GS (Group Separator)",
    b"\x1E": "RS (Record Separator)",
    b"\x1F": "US (Unit Separator)",
    b"\x7F": "DEL (Delete)",
}


roll_data = []
pitch_data = []
yaw_data = []

fig, ax = plt.subplots()


def update_plot():
    ax.clear()  # グラフをクリア
    ax.plot(roll_data, label="Roll")
    ax.plot(pitch_data, label="Pitch")
    ax.plot(yaw_data, label="Yawing")
    ax.legend()
    plt.draw()
    plt.pause(0.01)


ani = FuncAnimation(fig, update_plot, interval=1000)


async def add_data_for_plot(data):
    global roll_data, pitch_data, yaw_data
    roll_data.append(data[0])
    pitch_data.append(data[1])
    yaw_data.append(data[2])
    # リストが長くなりすぎないように制限
    if len(roll_data) > 100:
        roll_data.pop(0)
        pitch_data.pop(0)
        yaw_data.pop(0)
    update_plot()


async def readerAndWriter(loop):
    # logging.basicConfig(level=logging.INFO)

    # serial port setting
    port = "COM4"
    baudrate = 9600
    bytesize = 8
    parity = "N"
    stopbits = 1
    timeout = 0
    xonxoff = False
    rtscts = False
    dsrdtr = False
    waite_time = 0.1

    transport = None
    protocol = None

    try:
        transport, protocol = await serial_asyncio.create_serial_connection(
            loop, AsyncSerialCommunicator, port, baudrate=baudrate
        )

        while True:
            await asyncio.sleep(waite_time)

            # await protocol.serial_communication.send_string_as_byte(
            #     chr(0x02)
            #     + "Yesterday,I had an accident.\nI was cleaning my room.\nI used the vacuum cleaner.\nI pulled the chair and cleaned under it.\nThen I pulled the desk and cleaned under it.\nI wanted to cleaned under the bed next.\n"
            # )

            test = await protocol.serial_communication.read_serial_data_as_byte_list()
            # test = await protocol.serial_communication.read_line_as_bytes()
            # print(test)
            wit_test = await DataParser.witmotion_standard_protocol_angular(test)
            print(wit_test)
            if wit_test is not None:
                await add_data_for_plot(wit_test)

    except asyncio.CancelledError:
        print("Task was cancelled")

    finally:
        if protocol is not None:
            protocol.serial_communication.close_port()
        if transport is not None:
            transport.close()


async def main(loop):
    task = loop.create_task(readerAndWriter(loop))
    try:
        await task

    except asyncio.CancelledError:
        print("Task was cancelled")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    plt.show(block=False)
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
