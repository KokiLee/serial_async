import asyncio
import configparser
import cProfile
import logging
import math
import queue
import threading
from logging.handlers import RotatingFileHandler

import matplotlib.pyplot as plt
import numpy as np
import serial
import serial_asyncio
from matplotlib.animation import FuncAnimation

from constants import ascii_control_codes

handler = RotatingFileHandler("app.log", maxBytes=6000000, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


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
        logger.info("port opend", transport)

    async def send_string_as_byte(self, writestr: str):
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.transport.write, writestr.encode())
            logger.info("Send", self.transport)
            return True
        except Exception as e:
            logger.error(f"Failed to send data: {e}")
            return False

    async def read_serial_data_as_byte_list(self):
        data = bytearray()
        try:
            if self.transport.serial.in_waiting > 0:
                data.extend(
                    self.transport.serial.read(self.transport.serial.in_waiting)
                )
            return bytes(data)
        except Exception as e:
            logger.error(f"Failed to receive data: {e}")
            return False

    async def read_line_as_bytes(self):
        bytelist = []
        try:
            byteall = self.transport.serial.readline()
            for i in byteall:
                bytelist.append(i.to_bytes(1, "big"))
            return bytelist
        except Exception as e:
            logger.error(f"Failed to receive data: {e}")
            return bytelist

    def close_port(self):
        if self.transport:
            self.transport.close()
            logger.info("Serial port closed")


class DataParser:
    @staticmethod
    async def byte_to_ascii(
        byteData: bytes,
        dec: str = "utf-8",
        startText: bytes = b"\x02",
        endText: bytes = b"\x03",
    ):
        """Please specify the character encoding using the dec argument if it differs. The default is utf-8."""
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
                logger.error(f"No data: {e}")

    @staticmethod
    async def parity_check(
        byteData: bytes,
        startText: bytes = b"\x02",
        endText: bytes = b"*",
        initialValue: int = 0,
    ):
        """Generates a checksum between starttext and endtext.
        starttext and endtext specify start data and end data.
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
                logger.error(f"Fail parity check: {e}")
                return False


class HWT905_TTL_Dataparser:
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
    async def protocol_angular_output(data):
        previous_roll = 0
        previous_pitch = 0
        previous_yaw = 0
        direction = 0
        roll = None
        pitch = None
        yaw = None
        try:
            for i in range(len(data) - 1):
                if data[i] == 0x55 and data[i + 1] == 0x53:
                    # Byte value: An integer representing a single byte. Example: 85 or 0x55
                    # Byte string: A sequence containing one or more byte values. Example: b"\x55"

                    # Combine as a byte sequence.
                    roll_L_H = bytes([data[i + 2], data[i + 3]])
                    combined_roll = int.from_bytes(
                        roll_L_H, byteorder="little", signed=True
                    )
                    roll = combined_roll / 32768.0 * 180

                    pitch_L_H = bytes([data[i + 4], data[i + 5]])
                    combined_pitch = int.from_bytes(
                        pitch_L_H, byteorder="little", signed=True
                    )
                    pitch = combined_pitch / 32768.0 * 180

                    yaw_L_H = bytes([data[i + 6], data[i + 7]])
                    combined_yaw = int.from_bytes(
                        yaw_L_H, byteorder="little", signed=True
                    )
                    yaw = combined_yaw / 32768.0 * 180

                    # Implemented a solution to correct overflow and underflow in sensor data processing.
                    roll = await HWT905_TTL_Dataparser.adjust_angle_async(
                        roll, previous_roll
                    )
                    pitch = await HWT905_TTL_Dataparser.adjust_angle_async(
                        pitch, previous_pitch
                    )
                    yaw = await HWT905_TTL_Dataparser.adjust_angle_async(
                        yaw, previous_yaw
                    )
            return roll, pitch, yaw

        except Exception as e:
            logger.error("Data doesn't match")

    @staticmethod
    async def protocol_magnetic_field_output(data):
        direction = 0
        for i in range(len(data) - 1):
            if data[i] == 0x55 and data[i + 1] == 0x54:
                hxl_hxh = bytes([data[i + 2], data[i + 3]])
                hyl_hyh = bytes([data[i + 4], data[i + 5]])
                hzl_hzh = bytes([data[i + 6], data[i + 7]])

                combined_x = int.from_bytes(hxl_hxh, byteorder="little", signed=True)
                combined_y = int.from_bytes(hyl_hyh, byteorder="little", signed=True)
                combined_z = int.from_bytes(hzl_hzh, byteorder="little", signed=True)

                magnetic_strength = math.sqrt(
                    combined_x**2 + combined_y**2 + combined_z**2
                )
                direction = math.atan2(combined_y, combined_x) * (180 / math.pi)
                if direction < 0:
                    direction += 360

        return direction


class DataPlotter:
    def __init__(self) -> None:
        self.data_queue = queue.Queue()
        self.roll_data = []
        self.pitch_data = []
        self.yaw_data = []
        self.roll_line = None
        self.pitch_line = None
        self.yaw_line = None

    def update_plot(self, _):
        while not self.data_queue.empty():
            data = self.data_queue.get_nowait()
            if data is None:
                continue
            self.roll_data.append(data[0])
            self.pitch_data.append(data[1])
            self.yaw_data.append(data[2])
            if len(self.roll_data) > 100:
                self.roll_data.pop(0)
                self.pitch_data.pop(0)
                self.yaw_data.pop(0)

        if self.roll_line is not None:
            self.roll_line.set_data(range(len(self.roll_data)), self.roll_data)
            self.pitch_line.set_data(range(len(self.pitch_data)), self.pitch_data)
            self.yaw_line.set_data(range(len(self.yaw_data)), self.yaw_data)
            self.ax.relim()
            self.ax.autoscale_view()

    def add_data(self, data):
        self.data_queue.put(data)

    def set_ax(self, ax):
        self.ax = ax
        (self.roll_line,) = self.ax.plot([], [], label="Roll")
        (self.pitch_line,) = self.ax.plot([], [], label="Pitch")
        (self.yaw_line,) = self.ax.plot([], [], label="Yaw")
        self.ax.legend()


class DirectionPlotter:
    def __init__(self) -> None:
        self.data_queue = queue.Queue()
        self.directions = []
        self.arrow = None

    def update_plot(self, _):
        if not self.data_queue.empty():
            data = self.data_queue.get_nowait()
            if data is None:
                return
            rad = np.deg2rad(data)
            # self.ax.clear()
            if self.arrow is None:
                self.arrow = self.ax.quiver(
                    0,
                    0,
                    np.cos(rad),
                    np.sin(rad),
                    angles="xy",
                    scale_units="xy",
                    scale=1,
                    color="r",
                )
            else:
                self.arrow.set_UVC(np.cos(rad), np.sin(rad))

    def set_ax(self, ax):
        self.ax = ax
        self.setup_plot()

    def setup_plot(self):
        self.ax.set_xlim(-1, 1)
        self.ax.set_ylim(-1, 1)
        self.ax.grid(True)
        self.ax.set_aspect("equal", "box")
        self.ax.axhline(y=0, color="k")
        self.ax.axvline(x=0, color="k")

    def add_data(self, direction_data):
        self.data_queue.put(direction_data)


class CombinedPlotter:
    def __init__(self, angular_plotter, direction_plotter) -> None:
        self.fig, self.axs = plt.subplots(nrows=1, ncols=2, figsize=(9, 3))
        self.angular_plotter = angular_plotter
        self.direction_plotter = direction_plotter

        self.angular_plotter.set_ax(self.axs[0])
        self.direction_plotter.set_ax(self.axs[1])

        self.ani = FuncAnimation(
            self.fig, self.update_plots, interval=100, save_count=300
        )

    def update_plots(self, _):
        self.angular_plotter.update_plot(_)
        self.direction_plotter.update_plot(_)

    def show(self):
        plt.show()


class AsyncSerialManager:
    def __init__(
        self,
        port,
        baudrate,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=None,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
        waittime=0.1,
        angular_plotter=None,
        direction_plotter=None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        self.dsrdtr = dsrdtr
        self.waittime = waittime

        self.protocol = None
        self.transport = None

        self.angular_plotter = angular_plotter
        self.direction_plotter = direction_plotter

    def start_asyncio_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.sensor_angular_output_reader())
        self.loop.close()

    async def sensor_angular_output_reader(self):
        loop = asyncio.get_running_loop()
        try:
            self.transport, self.protocol = (
                await serial_asyncio.create_serial_connection(
                    loop,
                    AsyncSerialCommunicator,
                    self.port,
                    baudrate=self.baudrate,
                )
            )

            while True:
                await asyncio.sleep(self.waittime)

                raw_angular_output_data = (
                    await self.protocol.serial_communication.read_serial_data_as_byte_list()
                )

                angular_output_data = (
                    await HWT905_TTL_Dataparser.protocol_angular_output(
                        raw_angular_output_data
                    )
                )

                magnetic_field_output = (
                    await HWT905_TTL_Dataparser.protocol_magnetic_field_output(
                        raw_angular_output_data
                    )
                )

                if angular_output_data is not None:
                    logger.info(angular_output_data)
                    self.angular_plotter.add_data(angular_output_data)
                if magnetic_field_output is not None:
                    logger.info(magnetic_field_output)
                    self.direction_plotter.add_data(magnetic_field_output)

        except asyncio.CancelledError:
            print("Task was cancelled")

        except serial.SerialException as e:
            logger.error(f"Serial port {self.port} not opend: {e}")

        finally:
            if self.protocol is not None:
                self.protocol.serial_communication.close_port()
            if self.transport is not None:
                self.transport.close()


def main():  # 2つのサブプロットを作成
    direction_plotter = DirectionPlotter()
    angular_plotter = DataPlotter()
    combined_plotter = CombinedPlotter(angular_plotter, direction_plotter)
    combined_plotter.fig.suptitle("Angle and Magnetic field")
    combined_plotter.fig.canvas.manager.set_window_title(
        "Witmotion: HWT905-TTL MPU-9250"
    )

    asyncserialmanager = AsyncSerialManager(
        "COM4",
        9600,
        direction_plotter=direction_plotter,
        angular_plotter=angular_plotter,
    )
    async_thread = threading.Thread(target=asyncserialmanager.start_asyncio_loop)
    async_thread.daemon = True
    async_thread.start()

    combined_plotter.show()


if __name__ == "__main__":
    main()
