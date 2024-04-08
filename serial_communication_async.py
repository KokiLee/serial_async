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
from hwt905_ttl_dataparser import HWT905_TTL_Dataparser

handler = RotatingFileHandler("app.log", maxBytes=6000000, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


# 非同期IOを使用してシリアル通信を行うためのクラス。
# asyncio.Protocolを継承しており、非同期IOのコールバックメソッドをオーバーライドしている、
class AsyncSerialCommunicator(asyncio.Protocol):
    # called by asyncio when establishment a connection.
    # Save transport object to instance variable and Make instance of SrialCommunication class.
    # "Request to send" to disable.
    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"Port Opened: {transport}")
        transport.serial.rts = False
        self.serial_communication = SerialCommunication(transport)

    # data-received-class is for data receive. data-received-class called by asyncio.
    # This method displays receive data. data reading paused.
    def data_received(self, data):
        logger.info(f"data received: {repr(data)}")
        self.pause_reading()

    # called by asyncio when connection lost. "exc" parameter is an exception object.
    # if the connection is correctly closed,no exception will occur.
    def connection_lost(self, exc):
        self.transport.loop.stop()

    # if writing buffer is upper limmit,called by asyncio.
    def pause_writing(self):
        logger.info("pause writing")
        logger.info(self.transport.get_write_buffer_size())

    # Called by asyncio when writing buffer is the acceptable range.
    # This method is used to resume writing.
    def resume_writing(self):
        logger.info(self.transport.get_write_buffer_size())
        logger.info("resume writing")

    # This method is used to pause data reading.
    # If data processing data takes a long time, or buffer overflow prevents reading, reading may be paused.
    def pause_reading(self):
        self.transport.pause_reading()

    # This method resumes reading paused data.
    def resume_reading(self):
        self.transport.resume_reading()


# シリアルポートを介してデータの送受信を行うためのクラス。
# 送信するデータをバイト列に変換し、受信したデータをバイト列のリストとして処理。
class SerialCommunication:
    def __init__(self, transport) -> None:
        self.transport = transport

    async def send_string_as_byte(self, writestr: str):
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.transport.write, writestr.encode())
            logger.info(f"Send: {self.transport}")
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


# 受信したバイト列データを解析し、ASCII文字列に変換したり、BCCチェックを行う。
# 固有のものは別ファイルにして、一般的なものをここに記述する。
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


# 角度データをグラフにプロットするクラス。
# HWT905 TTL専用。ロー、ピッチ、ヨーのデータをグラフにリアルタイムでプロットする。
class AngularPlotter:
    def __init__(self) -> None:
        self.roll_data = []
        self.pitch_data = []
        self.yaw_data = []
        self.roll_line = None
        self.pitch_line = None
        self.yaw_line = None

    def update_plot(self, _):
        if self.roll_data and self.roll_data[-1] is not None:
            self.roll_text.set_text(f"Roll: {self.roll_data[-1]:.2f}")

        if self.pitch_data and self.pitch_data[-1] is not None:
            self.pitch_text.set_text(f"Pitch: {self.pitch_data[-1]:.2f}")

        if self.yaw_data and self.yaw_data[-1] is not None:
            self.yaw_text.set_text(f"Yaw: {self.yaw_data[-1]:.2f}")

        if (
            self.roll_line is not None
            and self.pitch_line is not None
            and self.yaw_line is not None
        ):
            self.roll_line.set_data(range(len(self.roll_data)), self.roll_data)
            self.pitch_line.set_data(range(len(self.pitch_data)), self.pitch_data)
            self.yaw_line.set_data(range(len(self.yaw_data)), self.yaw_data)
            self.ax.relim()
            self.ax.autoscale_view()

    def add_data(self, data):
        self.roll_data.append(data[0])
        self.pitch_data.append(data[1])
        self.yaw_data.append(data[2])

        if len(self.roll_data) > 100:
            self.roll_data.pop(0)
            self.pitch_data.pop(0)
            self.yaw_data.pop(0)

    def set_ax(self, ax):
        self.ax = ax
        (self.roll_line,) = self.ax.plot([], [], label="Roll")
        (self.pitch_line,) = self.ax.plot([], [], label="Pitch")
        (self.yaw_line,) = self.ax.plot([], [], label="Yaw")

        self.roll_text = self.ax.text(
            0.0,
            1.06,
            "Roll: N/A",
            transform=self.ax.transAxes,
            verticalalignment="top",
            color="blue",
        )
        self.pitch_text = self.ax.text(
            0.3,
            1.06,
            "Pitch: N/A",
            transform=self.ax.transAxes,
            verticalalignment="top",
            color="orange",
        )
        self.yaw_text = self.ax.text(
            0.6,
            1.06,
            "Yaw: N/A",
            transform=self.ax.transAxes,
            verticalalignment="top",
            color="green",
        )
        self.ax.legend()


# 磁場の方向と強さをグラフにプロットする。
# matplotlibのquiver関数を使用して、磁場の方向を矢印で表示する。磁力は数値
class DirectionPlotter:
    def __init__(self) -> None:
        self.rad = 0
        self.magnetic_strength = 0
        self.arrow = None

    def update_plot(self, _):
        if self.arrow is None:
            self.arrow = self.ax.quiver(
                0,
                0,
                np.cos(self.rad),
                np.sin(self.rad),
                angles="xy",
                scale_units="xy",
                scale=1,
                color="r",
            )
        else:
            self.arrow.set_UVC(np.cos(self.rad), np.sin(self.rad))

        if hasattr(self, "magnetic_strength_text"):
            self.magnetic_strength_text.set_text(
                f"Magnetic Strength: {self.magnetic_strength:.2f}"
            )
        else:
            self.magnetic_strength_text = self.ax.text(
                0.95,
                1.06,
                f"Magnetic Strength: {self.magnetic_strength:.2f}",
                verticalalignment="top",
                horizontalalignment="right",
                transform=self.ax.transAxes,
                color="blue",
                fontsize=10,
            )

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
        self.rad = np.deg2rad(direction_data[0])
        self.magnetic_strength = direction_data[1]


# 角度プロットと磁場磁力プロットをコンバインして二つのグラフを同時に表示する為のクラス。
class CombinedPlotter:
    def __init__(self, angular_plotter, direction_plotter, data_processor) -> None:
        self.fig, self.axs = plt.subplots(nrows=1, ncols=2, figsize=(9, 4))
        self.angular_plotter = angular_plotter
        self.direction_plotter = direction_plotter
        self.data_processor = data_processor

        self.angular_plotter.set_ax(self.axs[0])
        self.direction_plotter.set_ax(self.axs[1])

        self.ani = FuncAnimation(
            self.fig, self.update_plots, interval=100, save_count=300
        )

    def update_plots(self, _):
        angular_output_data, magnetic_field_output = (
            self.data_processor.read_sensor_data()
        )
        if angular_output_data and magnetic_field_output:
            self.angular_plotter.add_data(angular_output_data)
            self.direction_plotter.add_data(magnetic_field_output)
            self.angular_plotter.update_plot(_)
            self.direction_plotter.update_plot(_)

    def show(self):
        plt.tight_layout()
        plt.show()


# 非同期IOを使用してシリアルポートを管理し、データの送受信を行うためのクラス。
# asyncioとserial_asyncioを使用して非同期にシリアル通信を行う。
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

    def run_async_data_processing(self, result_queue):
        async def run_async_tasks():
            open_connection_success = await self.open_serial_connection()
            if not open_connection_success:
                logger.error("Failed to open serial connection")
                return
            while True:
                data = await self.read_data()

                result_queue.put(data)

        # 既存のイベントループを取得
        # loop = asyncio.get_event_loop()
        # # 非同期タスクをイベントループにスケジュール
        # asyncio.run_coroutine_threadsafe(run_async_tasks(), loop=loop)

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_async_tasks())
            finally:
                loop.close()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    async def open_serial_connection(self):
        loop = asyncio.get_event_loop()
        try:
            self.transport, self.protocol = (
                await serial_asyncio.create_serial_connection(
                    loop,
                    AsyncSerialCommunicator,
                    self.port,
                    baudrate=self.baudrate,
                    bytesize=self.bytesize,
                    parity=self.parity,
                    stopbits=self.stopbits,
                    timeout=self.timeout,
                    xonxoff=self.xonxoff,
                    rtscts=self.rtscts,
                    dsrdtr=self.dsrdtr,
                )
            )
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to open serial port {self.port}: {e}")
            return False

    async def read_data(self):
        await asyncio.sleep(self.waittime)
        raw_angular_output_data = None
        try:
            raw_angular_output_data = (
                await self.protocol.serial_communication.read_serial_data_as_byte_list()
            )
        except Exception as e:
            logger.error(f"Data none {e}")

        return raw_angular_output_data

    async def close_connection(self):
        if self.protocol is not None:
            self.protocol.serial_communication.close_port()
            logger.info("Closed port for protocol")
        if self.transport is not None:
            self.transport.close()
            logger.info("Close port for transport")


# 受信したデータを処理し、解析結果をCombinedPlotterクラスに渡すためのクラス。
# 受信データキューからデータを取得し、HWT905_TTL_Dataparserクラスを使用して解析を行う。
class DataProcessor:
    def __init__(self, read_data_queue) -> None:
        self.read_data_queue = read_data_queue

    def read_sensor_data(self):
        if not self.read_data_queue.empty():
            sensor_data = self.read_data_queue.get()

            angular_output_data = HWT905_TTL_Dataparser.protocol_angular_output(
                sensor_data
            )

            magnetic_field_output = (
                HWT905_TTL_Dataparser.protocol_magnetic_field_output(sensor_data)
            )

            return angular_output_data, magnetic_field_output
        else:
            return None, None


# プログラムのエントリーポイント。
# 各クラスのインスタンスを作成してプログラムを実行する。
def main():
    direction_plotter = DirectionPlotter()
    angular_plotter = AngularPlotter()

    result_queue = queue.Queue()

    asyncserialmanager = AsyncSerialManager(
        "COM5",
        9600,
        waittime=0.1,
    )

    asyncserialmanager.run_async_data_processing(result_queue=result_queue)

    dataprocessor = DataProcessor(result_queue)

    combined_plotter = CombinedPlotter(
        angular_plotter, direction_plotter, dataprocessor
    )

    combined_plotter.fig.suptitle("Angle and Magnetic field")

    combined_plotter.fig.canvas.manager.set_window_title(
        "Witmotion: HWT905-TTL MPU-9250"
    )

    combined_plotter.show()


if __name__ == "__main__":
    main()
