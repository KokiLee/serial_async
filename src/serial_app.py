import asyncio
import sys
import tkinter as tk

import qasync
from PyQt5.QtWidgets import QApplication

import serial_communication_async


async def main():
    asyncserialmanager = serial_communication_async.AsyncSerialManager(
        "COM4", 9600, waittime=0.1
    )
    dataprocessor = serial_communication_async.DataProcessor(
        asyncserialmanager.result_queue
    )

    # シリアル通信のタスクを開始
    task = asyncio.create_task(asyncserialmanager.run())

    direction_plotter = serial_communication_async.DirectionPlotter()
    angular_plotter = serial_communication_async.AngularPlotter()

    combined_plotter = serial_communication_async.CombinedPlotter(
        angular_plotter,
        direction_plotter,
        [],
        [],
    )

    # プロットの更新タスクを開始
    update_task = asyncio.create_task(
        serial_communication_async.update_plots(combined_plotter, dataprocessor)
    )

    main_window = serial_communication_async.MainWindow(
        combined_plotter, task, update_task
    )
    main_window.show()

    # シリアル通信とプロット更新のタスクを待機
    await asyncio.gather(task, update_task)

    await asyncserialmanager.close_connection()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
