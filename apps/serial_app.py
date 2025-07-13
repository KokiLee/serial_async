import asyncio
import configparser
import sys
import tkinter as tk

import qasync
from PyQt5.QtWidgets import QApplication

from src.serial_communication_async import (
    AngularPlotter,
    AsyncSerialManager,
    CombinedPlotter,
    DataProcessor,
    DirectionPlotter,
    MainWindow,
    update_plots,
)

config = configparser.ConfigParser()
config.read("config/config.ini")

port = config.get("serial_set", "portname")
baudrate = config.get("serial_set", "baudrate")
timeout = config.get("serial_set", "timeout")
stopbits = config.get("serial_set", "stopbits")
bytesize = config.get("serial_set", "bytesize")
parity = config.get("serial_set", "parity")
xonxoff = config.get("serial_set", "xonxoff")
read_wait_time = config.get("serial_set", "readwait")


async def main():
    asyncserialmanager = AsyncSerialManager(
        port=port,
        baudrate=baudrate,
        waittime=float(read_wait_time),
        bytesize=int(bytesize),
        stopbits=int(stopbits),
        parity=parity,
        timeout=int(timeout),
        xonxoff=bool(xonxoff),
    )
    dataprocessor = DataProcessor(asyncserialmanager.result_queue)

    # シリアル通信のタスクを開始
    task = asyncio.create_task(asyncserialmanager.run())

    direction_plotter = DirectionPlotter()
    angular_plotter = AngularPlotter()

    combined_plotter = CombinedPlotter(
        angular_plotter,
        direction_plotter,
        [],
        [],
    )

    # プロットの更新タスクを開始
    update_task = asyncio.create_task(update_plots(combined_plotter, dataprocessor))

    main_window = MainWindow(combined_plotter, task, update_task)
    main_window.show()

    # シリアル通信とプロット更新のタスクを待機
    await asyncio.gather(task, update_task)

    await asyncserialmanager.close_connection()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
