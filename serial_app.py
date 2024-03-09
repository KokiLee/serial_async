import asyncio
import queue
import threading
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import serial_communication_async


def main():
    root = tk.Tk()
    root.title("Serial Data Plot")

    angular_plotter = serial_communication_async.AngularPlotter()
    direction_plotter = serial_communication_async.DirectionPlotter()

    result_queue = queue.Queue()

    asyncserialmanager = serial_communication_async.AsyncSerialManager(
        "COM4", 9600, waittime=0.1
    )

    asyncserialmanager.run_async_data_processing(result_queue=result_queue)

    dataprocessor = serial_communication_async.DataProcessor(result_queue)

    combined_plotter = serial_communication_async.CombinedPlotter(
        angular_plotter, direction_plotter, dataprocessor
    )
    combined_plotter.fig.suptitle("Angle and Magnetic field")

    canvas = FigureCanvasTkAgg(combined_plotter.fig, master=root)
    canvas_weight = canvas.get_tk_widget()
    canvas_weight.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
