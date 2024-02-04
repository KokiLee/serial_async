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
        print("Port Opened", transport)
        transport.serial.rts = False
        transport.write(b"Hellow, World!\n")

    def data_received(self, data):
        print("Data Received", repr(data))

    def connection_lost(self, exc):
        print("Port Closed")
        asyncio.get_event_loop().stop()


class SerialConfig:
    def __init__(self, transport) -> None:
        self.transport = transport

    def port_open(self):
        try:
            self.transport.open()
            return self.transport.serial.isOpen()
        except Exception as e:
            logging.error(f"Failed to open port: {e}")
            return False

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

    async def readbyte(self):
        bytelist = []
        try:
            if self.in_waiting > 0:
                for i in range(self.transport.serial.in_waiting):
                    bytelist.append(self.transport.serial.read())
                print(type(bytelist[1]))
                return "Read Start\n", bytelist
            else:
                return "Read Faile\n", bytelist
        except Exception as e:
            logging.error(f"Failed to receive data: {e}")
            return "Read Faile\n", bytelist

    async def readallbyte(self):
        bytelist = []
        try:
            byteall = self.readline()
            print(byteall)
            for i in byteall:  # type: ignore
                bytelist.append(i.to_bytes(1, "big"))
            return "Read Start\n", bytelist
        except Exception as e:
            logging.error(f"Failed to receive data: {e}")
            return "Read Faile\n", bytelist


class DataParser:
    @staticmethod
    def byte_to_ascii(self, bytelist: list, dec: str = "utf-8"):
        """文字コードが違う場合は引数 dec で指定してください。デフォルトは utf-8"""
        decli = []
        try:
            if b"\x02" == bytelist[0]:
                for i in bytelist:
                    decli.append(i.decode(dec))
                    x = "".join(decli)
                    if b"\x03" in i:
                        break
                return x  # type: ignore
        except:
            return ""

    @staticmethod
    async def parity_check(
        lineData: str,
        startText: bytes = b"\x02",
        endText: bytes = b"*",
        initialValue: int = 0,
    ):
        """startText から endText の間でチェックコードを生成します。initialValue は初期値"""
        try:
            processing = False
            for i in lineData:
                if startText == endText:
                    return ""

                if i.encode() == startText:
                    processing = True
                    continue
                elif i.encode() == endText:
                    break
                if processing:
                    initialValue ^= ord(i)

            return format(initialValue, "02x")
        except Exception as e:
            return ""


# --- GUI ---
class Tk_Button(tk.Button):
    def __init__(self, master=None, cnf={}, **kw):
        tk.Button.__init__(self, master, cnf, **kw)
        self.configure(
            font=("", 9),
            text="ボタン",
            width=30,
        )
        self.configure(**kw)


class App(tk.Frame, AsyncSerialCommunicator):
    def __init__(self, root) -> None:
        super().__init__(root, width=380, height=180, borderwidth=3, relief="groove")
        self.root = root
        self.pack()
        self.pack_propagate(True)
        self.create_widgets()
        self.seri = AsyncSerialCommunicator()

    def text_box(self):
        pass

    def create_widgets(self):
        self.open_btn = tk.Button(self)
        self.open_btn["text"] = "Port Open"
        self.open_btn["state"] = "normal"
        self.open_btn["command"] = lambda: self.port_open_hold()
        self.open_btn.pack(side="left")

        self.close_btn = tk.Button(self)
        self.close_btn["text"] = "Port Close"
        self.close_btn["state"] = "disable"
        self.close_btn["command"] = lambda: self.port_close()
        self.close_btn.pack(side="left")

        self.read_btn = tk.Button(self)
        self.read_btn["text"] = "Reading"
        self.read_btn["state"] = "disable"
        self.read_btn["command"] = lambda: self.read_start()
        self.read_btn.pack(side="left")

        test_btn = tk.Button(self)
        test_btn["text"] = "testread"
        test_btn["command"] = lambda: self.test_writing()
        test_btn.pack(side="bottom")

    def port_open_hold(self):
        self.open_btn["state"] = "disable"
        self.close_btn["state"] = "normal"
        self.read_btn["state"] = "normal"
        print(self.seri.portopen())

    def port_close(self):
        self.open_btn["state"] = "normal"
        self.close_btn["state"] = "disable"
        self.read_btn["state"] = "disable"
        self.after_cancel(self.after_id)
        self.after_cancel(self.test_end)
        print(self.seri.portclose())

    def serial_read(self):
        if self.seri.in_waiting > 0:
            self.after(150, lambda: print(self.seri.serial_test()))
        self.read_start()

    def test_writing(self):
        print(
            self.seri.writebyte(
                chr(0x02)
                + "0_0,0_0,0_0,0_0,0_0,0_0,0_0,0_0,0_0,100_0,51_0,-0.1_0,-0.1_0,0_0,0.12_0,0.12_0,0.12_0,0.12_0,0.12_0,0.12_0,0.12_0,0.12_0*"
                + chr(0x03)
            )
        )
        self.test_end = self.after(1000, lambda: self.test_writing())

    def read_start(self):
        self.read_btn["state"] = "disable"
        if self.read_btn["state"] == tk.DISABLED:
            self.after_id = self.after(150, lambda: self.serial_read())


config = configparser.ConfigParser()
config["serial_set"] = {  # type: ignore
    "portname": "COM3",
    "baudrate": 9600,
    "timeout": 3,
    "stopbits": 1,
    "bytesize": 8,
    "parity": "N",
    "xonxoff": "True",
}
config.read("config.ini")
read_base = config["serial_set"]
if not os.path.exists("config.ini"):
    with open("config.ini", "w+") as file:
        config.write(file)

root = tk.Tk()
root.geometry("640x480")
root.title("Serial")
root["bg"] = "#e0ffff"


app = App(root)

if __name__ == "__main__":
    root.mainloop()
