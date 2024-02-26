import threading
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import serial_communication_async


def main():
    root = tk.Tk()
    root.title("Serial Data Plot")

    angular_plotter = serial_communication_async.DataPlotter()
    direction_plotter = serial_communication_async.DirectionPlotter()
    combined_plotter = serial_communication_async.CombinedPlotter(
        angular_plotter, direction_plotter
    )
    combined_plotter.fig.suptitle("Angle and Magnetic field")

    canvas = FigureCanvasTkAgg(combined_plotter.fig, master=root)
    canvas_weight = canvas.get_tk_widget()
    canvas_weight.pack(fill=tk.BOTH, expand=True)

    asyncserialmanager = serial_communication_async.AsyncSerialManager(
        "COM4",
        9600,
        direction_plotter=direction_plotter,
        angular_plotter=angular_plotter,
    )
    async_thread = threading.Thread(target=asyncserialmanager.start_asyncio_loop)
    async_thread.daemon = True
    async_thread.start()

    root.mainloop()


if __name__ == "__main__":
    main()
