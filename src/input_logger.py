#!/usr/bin/env python3
import time
from pymongo import MongoClient
from config import HOSTNAME, PORT, DATABASE, KEYBOARD_COLLECTION, MOUSE_COLLECTION, APPLICATION_COLLECTION
from pynput import mouse, keyboard
from datetime import datetime
from models import MouseInput, KeyboardInput, ApplicationData
import pyautogui
import win32gui
from concurrent.futures import ThreadPoolExecutor

client = MongoClient(HOSTNAME, PORT)
db = client[DATABASE]
keyboard_coll = db[KEYBOARD_COLLECTION]
mouse_coll = db[MOUSE_COLLECTION]
app_coll = db[APPLICATION_COLLECTION]

executor = ThreadPoolExecutor(max_workers=100)


def close_executor():
    executor.shutdown(wait=True, cancel_futures=True)


def insert_data(collection, data):
    collection.insert_one(data.model_dump())


def insert_app_data():
    global prev_apps, prev_focused
    focused_app = win32gui.GetWindowText(win32gui.GetForegroundWindow())
    pyauto_apps = pyautogui.getAllTitles()
    open_apps = []
    for title in pyauto_apps:
        if len(title) > 0:
            open_apps.append(title)
    if open_apps == prev_apps and focused_app == prev_focused: return
    app_data = ApplicationData(timestamp=datetime.now(),
                               focused_app=focused_app,
                               visible_apps=open_apps)
    app_coll.insert_one(app_data.model_dump())
    prev_apps = open_apps
    prev_focused = focused_app


def on_move(x, y):
    global prev_mouse_move_time
    if (time.time() - prev_mouse_move_time) < 0.1: return
    prev_mouse_move_time = time.time()
    mouse_input = MouseInput(timestamp=datetime.now(),
                             x=x,
                             y=y,
                             right_click=False,
                             left_click=False,
                             middle_click=False,
                             scroll=0)
    executor.submit(insert_data, mouse_coll, mouse_input)


def on_click(x, y, button, pressed):
    if not pressed: return
    right_click = button == mouse.Button.right
    left_click = button == mouse.Button.left
    middle_click = button == mouse.Button.middle
    mouse_input = MouseInput(timestamp=datetime.now(),
                             x=x,
                             y=y,
                             right_click=right_click,
                             left_click=left_click,
                             middle_click=middle_click,
                             scroll=0)
    executor.submit(insert_data, mouse_coll, mouse_input)
    executor.submit(insert_app_data)


def on_scroll(x, y, dx, dy):
    mouse_input = MouseInput(timestamp=datetime.now(),
                             x=x,
                             y=y,
                             right_click=False,
                             left_click=False,
                             middle_click=False,
                             scroll=dy)
    executor.submit(insert_data, mouse_coll, mouse_input)


def on_release(key):
    keyboard_input = KeyboardInput(timestamp=datetime.now(),
                                   key_value=format(key))
    executor.submit(insert_data, keyboard_coll, keyboard_input)


def create_input_listeners():
    global prev_mouse_move_time, prev_apps, prev_focused
    prev_mouse_move_time = time.time()
    prev_apps = []
    prev_focused = ""
    mouse_listener = mouse.Listener(on_move=on_move,
                                    on_click=on_click,
                                    on_scroll=on_scroll)
    keyboard_listener = keyboard.Listener(on_release=on_release)
    mouse_listener.start()
    keyboard_listener.start()
    return list([mouse_listener, keyboard_listener])


def stop_input_listeners(listeners):
    for listener in listeners:
        listener.stop()
