"""This program is from When I started learning python"""
import configparser
import datetime
import os
import re
import subprocess
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import numpy as np
import serial
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ser = None
afterid = None
y = [0, 0, 0, 0, 0, 0, 0]
f_list = [0, 0, 0, 0, 0, 0, 0, 0]
e_list = [0, 0, 0, 0, 0, 0, 0, 0]
ax_list = []

pres = ""

config = configparser.ConfigParser()
config["serial_set"] = {  # type: ignore
    "portname": "COM4",
    "baudrate": 9600,
    "timeout": 3,
    "stopbits": 1,
    "bytesize": 8,
    "parity": "N",
    "xonxoff": "True",
    "readwait": 0.1,
}

config.read("config.ini")
read_base = config["serial_set"]

if not os.path.exists("config.ini"):
    with open("config.ini", "w+") as file:
        config.write(file)


class User_button(tk.Button):
    def __init__(self, master=None, cnf={}, **kw):
        tk.Button.__init__(self, master, cnf, **kw)
        self.configure(
            font=("", 9),
            bg="#fffaf0",
            fg="black",
            width=9,
            padx=3,
            pady=3,
            state="normal",
        )
        self.configure(**kw)


# 水平パリティ生成　2バイト
def lrc(str1: str, byte1: bytes = b"\x02", byte2: bytes = b"*", init: int = 0):
    int_list = []
    for i in str1:
        if i.encode() == byte2:
            break
        if i.encode() != byte1:
            int_list.append(int.from_bytes(i.encode(), "big"))
    p = init
    hex_list = []
    for i in int_list:
        hex_list.append(hex(i))
        p = i ^ p
    p = str.upper(format(p, "02x"))
    print(p)
    # print(hex_list)
    return p


# raspi で書き換え "start" >- "mousepad" shell=true 削除
def set_fun():
    subprocess.Popen(["mousepad", "config.ini"])


def help_():
    subprocess.Popen(["mousepad", "manual.txt"])


def port_open():
    global ser

    try:
        open_button.configure(state="disabled", bg="#d3d3d3")
        close_button.configure(state="normal", bg="#fffaf0")
        read_button.configure(state="normal", bg="#fffaf0")

        port = read_base.get("portname")
        baudrate_ = read_base.getint("baudrate")
        timeout_ = read_base.getfloat("timeout")
        stopbits_ = read_base.getint("stopbits")
        bytesize_ = read_base.getint("bytesize")
        parity_ = read_base.get("parity")

        # ser = serial.Serial(port,baudrate_,timeout=timeout_,
        # bytesize=bytesize_,stopbits=stopbits_,parity=parity_)

        ser = serial.Serial()
        ser.port = port
        ser.baudrate = baudrate_
        ser.timeout = timeout_
        ser.stopbits = stopbits_
        ser.bytesize = bytesize_
        ser.parity = parity_
        ser.xonxoff = False
        ser.rtscts = False
        ser.dsrdtr = False

        ser.open()

        contents.insert(tk.END, "---Port Open---\n", "open")
        contents.see("end")
        return ser
    except:
        open_button.configure(state="normal", bg="#fffaf0")
        close_button.configure(state="disabled", bg="#d3d3d3")
        read_button.configure(state="disabled", bg="#d3d3d3")

        contents.insert(tk.END, "---Port Error---\n", "error")
        contents.see("end")


def port_close():
    read_button.configure(state="disabled", bg="#d3d3d3")
    open_button.configure(state="normal", bg="#fffaf0")
    close_button.configure(state="disabled", bg="#d3d3d3")

    ser.close()  # type: ignore
    contents.insert(tk.END, "---Port Close---\n", "close")
    contents.see("end")


def serial_read(enc: str):
    global afterid
    global np_list
    readwait = read_base.getfloat("readwait")
    if open_button["state"] == tk.DISABLED:
        read_button.configure(state="disabled", bg="#d3d3d3")
        close_button.configure(state="disabled", bg="#d3d3d3")
        stop_button.configure(state="normal", bg="#fffaf0")
        test_button.configure(state="normal", bg="#fffaf0")
    # データ取得時間
    dt_now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    try:
        if ser.in_waiting > 0:  # type: ignore
            time.sleep(readwait)
            contents.insert(tk.END, "---Serial Read---" + dt_now + "\n", "read")

            line = ser.read_all()  # type: ignore
            ascii_ = line.decode(enc)
            byte_ = ascii_.encode()
            int_byte = int.from_bytes(byte_, "big")
            hex_ascii = "HEX > {:02X}".format(int_byte)
            # print(line.decode("ascii"))
            if ascii_button["state"] == tk.DISABLED:
                cont_insert = "ASCII > " + ascii_.replace(chr(0x02), "STX").replace(
                    chr(0x03), "ETX\n"
                )
            if hex_button["state"] == tk.DISABLED:
                cont_insert = hex_ascii
                cont_insert = cont_insert + "\n"

            p_read = re.findall(r"\*(.*)", line.decode(enc))
            p_re_str = str.upper(p_read[0]).replace("\x03", "")

            p = lrc(ascii_, b"\x02", b"*", 0)

            if p == p_re_str:
                contents.insert(tk.END, cont_insert + "\n", "read_cont")  # type: ignore
                contents.see("end")
            else:
                contents.insert(tk.END, cont_insert + "\n", "read_cont_p")  # type: ignore
                contents.see("end")

            ascii_ = ascii_.replace("*", ",")

            a_list = ascii_.split(",")
            # print(a_list)
            if len(a_list) > 0:
                i1 = 0
                i2 = 0
                for i in a_list:
                    # print("." in i)
                    if "." in i:
                        try:
                            f_list[i1] = float(i)  # type: ignore
                            i1 += 1
                        except:
                            pass
                    elif "1" == i or "0" == i:
                        e_list[i2] = i
                        i2 += 1
            # print(f_list)
            print(e_list)

            # ------PLOT UPDATE------
            updateplt(0)

    except:
        contents.insert(tk.END, "---Device Error---\n", "error")
        contents.see("end")
    # 繰り返し実行
    if read_button["state"] == tk.DISABLED:
        afterid = root.after(1000, lambda: serial_read("ascii"))
        return afterid


def stop_read():
    global afterid
    read_button.configure(state="normal", bg="#fffaf0")
    stop_button.configure(state="disabled", bg="#d3d3d3")
    close_button.configure(state="normal", bg="#fffaf0")
    test_button.configure(state="disabled", bg="#d3d3d3")
    root.after_cancel(afterid)  # type: ignore
    afterid = None


def loop_back():
    time.sleep(0.5)
    y = (0 - 6.0) * np.random.rand(8) + 6.0
    level_arr = []
    for i in y:
        level_arr.append("{:.3f}".format(i))

    try:
        serialcommand = (
            chr(0x02)
            + ","
            + level_arr[0]
            + ","
            + "1,"
            + level_arr[1]
            + ","
            + "0,"
            + level_arr[2]
            + ","
            + "1,"
            + level_arr[3]
            + ",0,"
            + level_arr[4]
            + ",0,"
            + level_arr[5]
            + ",1,"
            + level_arr[6]
            + "*"
        )

        p = lrc(serialcommand, b"\x02", b"*", 0)

        serialcommand = serialcommand + p + chr(0x03)

        ser.write(serialcommand.encode())  # type: ignore
    except:
        contents.insert(tk.END, "---Device Error---\n", "error")
        contents.see("end")


def ascii_r():
    ascii_button.configure(state="disabled", bg="#d3d3d3")
    hex_button.configure(state="normal", bg="#fffaf0")
    # print(ascii_)


def hex_r():
    ascii_button.configure(state="normal", bg="#fffaf0")
    hex_button.configure(state="disabled", bg="#d3d3d3")


def save(event=None):
    # f_type = [("Text","*txt")]
    # filepath = tk.filedialog.asksaveasfilename(filetypes=f_type)

    # if filepath != "":
    with open("log.txt", "w", encoding="utf-8") as f:
        f.write(contents.get("1.0", "end-1c"))
    subprocess.Popen(["mousepad", "log.txt"])

    return


def set_update():
    config.read("config.ini")
    read_base = config["serial_set"]
    set_port_txt.set("PortName = " + read_base.get("portname"))
    set_baud_txt.set("Baudrate = " + read_base.get("baudrate"))
    set_stop_txt.set("Stopbits = " + read_base.get("stopbits"))
    set_byte_txt.set("ByteSize = " + read_base.get("bytesize"))
    set_parity_txt.set("Parity = " + read_base.get("parity"))
    set_tim_txt.set("Timeout = " + read_base.get("timeout"))
    frame.after(1000, set_update)


def sw_window(window):
    window.tkraise()
    root.geometry("690x450")


# ****************Matoplotlib**********************
art = []


def updateplt(u):
    # plt.cla()
    # test1=0
    # test1 = f_list[0] / 10 * i
    # plt.ion()
    for i1 in range(8):
        ax_list[i1].cla()
        # ax_list[i].grid(True)
        ax_list[i1].set_ylim(0, 6)
        ax_list[i1].set_yticks(np.arange(0, 6, step=1))
        if i1 >= 4:
            ax_list[i1].set_ylim(0, 12)
            ax_list[i1].set_yticks(np.arange(0, 12, step=1))

        ax_list[i1].tick_params(labelsize=9)

        ax_list[i1].set_title(
            "Level\n" + str(f_list[i1]),
            fontsize=9,
        )
        if e_list[i1] == "1":
            barcolor = "r"
        else:
            barcolor = "c"

        ax_list[i1].bar(x[i1], f_list[i1], width=0.6, color=barcolor)

    # ax_list[7].bar(x[7],0,width=0.6,color=barcolor)

    fig.canvas.draw()
    fig.canvas.flush_events()

    # ********axis Y word*******
    # for i in ax_list[i1].bar(x[i1],f_list[i1],width=0.3,color="c"):
    #     height = i.get_height()
    #     ax_list[i1].annotate("{}".format(height),
    #     xy=(i.get_x()+i.get_width() / 2,height),
    #     xytext=(0,3),
    #     textcoords="offset points",
    #     ha="center",va="bottom",
    #     fontsize=7.5
    #     )


def txtchange(str_: str, tset):
    a = lrc(str_, b"\02x", b"*")
    tset.set("Check Code HEX: " + a)


def newwindow():
    new_w = tk.Toplevel(root)
    new_w.geometry("570x120")
    new_w["bg"] = "#e0ffff"
    new_w.title("Check Code")

    fr = ttk.Frame(new_w, padding=6, width=300, height=200)
    fr.pack(side=tk.TOP)

    inbox = tk.Entry(fr, width=87, font=("", 12))
    inbox.pack(side=tk.TOP, expand=False, fill=tk.BOTH)

    text = tk.StringVar(new_w)
    go = User_button(fr, text="Check", command=lambda: txtchange(inbox.get(), text))
    go.pack(side=tk.LEFT, pady=6, expand=False)

    text.set("Check Code")

    res = tk.Label(fr, textvariable=text, bg="#e0ffff", font=("", 15, "bold"))
    res.pack(side=tk.LEFT, padx=3)


# ******GUI******
root = tk.Tk()
root.title("PySerialDisplay Read_Only")
root.geometry("690x450")
root["bg"] = "#e0ffff"
st = ttk.Style()
st.configure("TFrame", background="#e0ffff")
st.configure("TLabel", background="#e0ffff")

root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)

frame = ttk.Frame(root, padding=3, width=630, height=150)
frame.grid(row=0, column=0, pady=3, padx=3, sticky=tk.W)
frame.grid_propagate(0)  # type: ignore

frame2 = ttk.Frame(root, padding=3, width=630, height=102)
frame2.grid_propagate(0)  # type: ignore
frame2.grid(row=1, column=0, sticky=tk.NSEW)

frame1 = ttk.Frame(root, padding=3, width=630, height=90)
frame1.grid_propagate(0)  # type: ignore
frame1.grid(row=1, column=0, sticky=tk.NSEW)

# スクロールテキスト
contents = ScrolledText(frame1)
contents.pack(side=tk.TOP, expand=True, fill=tk.BOTH)
contents.tag_config(
    "error",
    background="red",
    foreground="#ffffff",
    font=("", 12, "bold"),
    justify=tk.CENTER,
)
contents.tag_config(
    "open",
    background="green",
    foreground="black",
    font=("", 12, "bold"),
    justify=tk.CENTER,
)
contents.tag_config(
    "close",
    background="yellow",
    foreground="black",
    font=("", 12, "bold"),
    justify=tk.CENTER,
)
contents.tag_config(
    "read",
    background="#66cdaa",
    foreground="black",
    font=("", 12, "bold"),
    justify=tk.LEFT,
)
contents.tag_config(
    "read_cont",
    background="#66cdaa",
    foreground="black",
    font=("", 12, "normal"),
    justify=tk.LEFT,
)
contents.tag_config(
    "read_cont_p",
    background="#f0e68c",
    foreground="black",
    font=("", 12, "normal"),
    justify=tk.LEFT,
)
# contents.bind("<Key>",lambda a: "break")

# OPEN
open_button = User_button(frame, text="OPEN", command=port_open)
open_button.place(x=6, y=3)

# CLOSE
close_button = User_button(frame, text="CLOSE", command=port_close)
close_button.place(x=90, y=3)
close_button.configure(state="disabled", bg="#d3d3d3")

# READ
read_button = User_button(frame, text="READ", command=lambda: serial_read("ascii"))
read_button.place(x=200, y=3)
read_button.configure(state="disabled", bg="#d3d3d3")

# STOP
stop_button = User_button(frame, text="STOP", command=stop_read)
stop_button.place(x=285, y=3)
stop_button.configure(state="disabled", bg="#d3d3d3")

# 下側*********************************************************
# TEST(loop back)
test_button = User_button(frame, text="TEST", command=loop_back)
test_button.place(x=200, y=66)
test_button.configure(state="disabled", bg="#d3d3d3")

# Clear
clear_button = User_button(
    frame, text="CLEAR", command=lambda: contents.delete("1.0", tk.END)
)
clear_button.place(x=285, y=66)

# ASCII READ
ascii_button = User_button(frame, text="ASCII", command=ascii_r)
ascii_button.place(x=6, y=66)
ascii_button.configure(state="disabled", bg="#d3d3d3")

# HEX READ
hex_button = User_button(frame, text="HEX", command=hex_r)
hex_button.place(x=90, y=66)

# setting info
set_port_txt = tk.StringVar()
set_baud_txt = tk.StringVar()
set_stop_txt = tk.StringVar()
set_byte_txt = tk.StringVar()
set_parity_txt = tk.StringVar()
set_tim_txt = tk.StringVar()
set_waittim_txt = tk.StringVar()

set_port_txt.set("PortName = " + read_base.get("portname"))
set_baud_txt.set("Baudrate = " + read_base.get("baudrate"))
set_stop_txt.set("Stopbits = " + read_base.get("stopbits"))
set_byte_txt.set("ByteSize = " + read_base.get("bytesize"))
set_parity_txt.set("Parity = " + read_base.get("parity"))
set_tim_txt.set("Timeout = " + read_base.get("timeout"))
set_waittim_txt.set("ReadWait = " + read_base.get("readwait"))

set_port = ttk.Label(frame, textvariable=set_port_txt)
set_port.place(x=420, y=0)
set_baud = ttk.Label(frame, textvariable=set_baud_txt)
set_baud.place(x=420, y=21)
set_stop = ttk.Label(frame, textvariable=set_stop_txt)
set_stop.place(x=420, y=42)
set_parity = ttk.Label(frame, textvariable=set_parity_txt)
set_parity.place(x=420, y=63)
set_byte = ttk.Label(frame, textvariable=set_byte_txt)
set_byte.place(x=420, y=84)
set_tim = ttk.Label(frame, textvariable=set_tim_txt)
set_tim.place(x=420, y=105)
set_tim = ttk.Label(frame, textvariable=set_waittim_txt)
set_tim.place(x=420, y=126)

set_update()

# メニューバー
menubar = tk.Menu(root)
root.configure(menu=menubar)

filemenu = tk.Menu(root, tearoff=0)
menubar.add_cascade(label="File", menu=filemenu)

filemenu.add_command(label="Setting", command=set_fun)
filemenu.add_command(label="Save", command=save)
filemenu.add_separator()
filemenu.add_command(label="Exit", command=lambda: root.destroy())

display_menu = tk.Menu(root, tearoff=0)
menubar.add_cascade(label="Display", menu=display_menu)
display_menu.add_command(label="Serial Read", command=lambda: sw_window(frame1))
display_menu.add_separator()
display_menu.add_command(label="Data", command=lambda: sw_window(frame2))

parity_menu = tk.Menu(root, tearoff=0)
menubar.add_cascade(label="CheckCode", menu=parity_menu)
parity_menu.add_command(label="Check", command=newwindow)

help_menu = tk.Menu(root, tearoff=0)
menubar.add_cascade(label="Help", menu=help_menu)
help_menu.add_command(label="Manual", command=help_)

# plot_histgram
x = np.array(["T1", "T2", "T3", "T4", "T5", "T6", "T7", "None"])

fig, ax1 = plt.subplots()
fig = plt.figure(figsize=(6.3, 3.36), dpi=100, facecolor="#e0ffff")
fig.subplots_adjust(wspace=3)

ax1 = fig.add_subplot(181)
ax2 = fig.add_subplot(182)
ax3 = fig.add_subplot(183)
ax4 = fig.add_subplot(184)
ax5 = fig.add_subplot(185)
ax6 = fig.add_subplot(186)
ax7 = fig.add_subplot(187)
ax8 = fig.add_subplot(188)

ax_list = [ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8]
# ---init updateplt---
updateplt(0)

canvas = FigureCanvasTkAgg(fig, frame2)
# type: ignore# ani = animation.FuncAnimation(fig, updateplt,
#                                     interval=1000,repeat=False,)
canvas.get_tk_widget().grid(row=0, column=0)
canvas.draw()
canvas.flush_events()

# root.after(10000,save)
if __name__ == "__main__":
    root.mainloop()
