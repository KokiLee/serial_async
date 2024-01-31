import asyncio
import configparser
import logging
import os
import tkinter as tk

import numpy as np
import serial_asyncio


# Ser class modify
class Transfer_serial_async(asyncio.Protocol):
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

    def port_open(self):
        try:
            self.transport.open()
            return self.transport.serial.isOpen()
        except Exception as e:
            logging.error(f"Failed to open port: {e}")
            return False

    def port_close(self):
        self.transport.close()
        return "Port Close"

    def send_string_as_byte(self, writestr: str):
        try:
            self.transport.write(writestr.encode())
            return "Send Start"
        except Exception as e:
            logging.error(f"Failed to send data: {e}")
            return False

    def readbyte(self):
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
            logging.error(f"Failed to read data: {e}")
            return "Read Faile\n", bytelist

    def readallbyte(self):
        bytelist = []
        try:
            byteall = self.readline()
            print(byteall)
            for i in byteall:  # type: ignore
                bytelist.append(i.to_bytes(1, "big"))
            return "Read Start\n", bytelist
        except:
            return "Read Faile\n", bytelist

    def bytetoascii(self, bytelist: list, dec: str = "utf-8"):
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

    def checkcode(
        self, word: str, sbyte: bytes = b"\x02", ebyte: bytes = b"*", initint: int = 0
    ):
        """sbyte から ebyte の間でチェックコードを生成します。initint は初期値"""
        int_list = []
        try:
            int_list = [
                int.from_bytes(i.encode(), byteorder="big")
                for i in word
                if i.encode() != sbyte
            ]
            for i in int_list:
                if i.to_bytes(2, "big") == b"\x00*":
                    break
                initint = initint ^ i
            return hex(initint)
        except:
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


class App(tk.Frame, Transfer_serial_async):
    def __init__(self, root) -> None:
        super().__init__(root, width=380, height=180, borderwidth=3, relief="groove")
        self.root = root
        self.pack()
        self.pack_propagate(True)
        self.create_widgets()
        self.seri = Transfer_serial_async()

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


# ---test code---
# ser = Ser()

# print(ser.portopen())

# # writestr = chr(0x02) + ", 2.068,0, 2.069,0, 2.070,0, 2.071,0, 4.040,0, 4.189,0, 4.190,0*16" + chr(0x03)
# writestr = chr(0x02) + "0_0,0_0,0_0,100_0,51_0,-0.1_0,0_0,0.12_0,0.12_0" + chr(0x03)
# print(ser.writebyte(writestr))

# readtext,readlist = ser.readbyte()
# print(readtext)
# print(readlist)
# print(ser.bytetoascii(readlist))
# print(ser.checkcode(ser.bytetoascii(readlist),ebyte=b"\x03"))  # type: ignore
# print(ser.portclose())

# ---test code---
