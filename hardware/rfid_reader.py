import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522, MFRC522
from services import handle

DEBOUNCE = 3.0   # giây , xử lý lỡ tay quẹt nhiều lần

class Reader(SimpleMFRC522):
    def __init__(self, device, pin_rst):
        self.READER = MFRC522(device=device, pin_rst=pin_rst)


entry_reader = Reader(device=0, pin_rst=22)   # CE0, RST GPIO25
exit_reader = Reader(device=1, pin_rst=18)    # CE1, RST GPIO24

last_entry = (None, 0)   # (uid, thời điểm)
last_exit = (None, 0)

try:
    print("Waiting for cards...")
    while True:
        now = time.time()

        rfid_uid = entry_reader.read_id_no_block()
        if rfid_uid and not (rfid_uid == last_entry[0] and now - last_entry[1] < DEBOUNCE):
            last_entry = (rfid_uid, now)
            print("ENTRY:", rfid_uid)
            

        rfid_uid = exit_reader.read_id_no_block()
        if rfid_uid and not (rfid_uid == last_exit[0] and now - last_exit[1] < DEBOUNCE):
            last_exit = (rfid_uid, now)
            print("EXIT:", rfid_uid)

        time.sleep(0.1)
finally:
    GPIO.cleanup()