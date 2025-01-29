"""_summary_
    To use this module, either
    1) Preferrable: pip install pynput  (https://pynput.readthedocs.io/en/latest/index.html)
    2) pip install keyboard (https://pypi.org/project/keyboard/)
    3) barcode should have \r (carriage return) as the last character,
    since input() of python only take keyboard input (scanner input) after getting carriage return
    Please visit https://barcode.tec-it.com/en to generate barcode    

"""

USE_PYNPUT = 1
USE_KEYBOARD = 0

if USE_PYNPUT:
    from pynput import keyboard
    from pynput.keyboard import Controller
if USE_KEYBOARD:
    import keyboard



class Scanner:

    def __init__(self):
        if USE_PYNPUT:
            self.Keyboard = Controller()
            self.barcodeList = list()
            self.listener = keyboard.Listener(
                on_press=self.__on_press)
            self.listener.start()

    #read barcode scanner as keyboard input. When received 12 bytes, type new line to trigger python function input() to capture the whole serial no.
    def __on_press(self, key):
        try:
            self.barcodeList.append(key.char)            
            if len(self.barcodeList) >= 12:
                self.Keyboard.type('\n')                
                self.listener.stop()
                self.barcodeList.clear()            
        except AttributeError:
            pass

    def getBarCode(self):
        """Get barcode from USB scanner

        Returns:
            string: scanned barcode, False if read serial no. is invalid (not 6ca401 in first 3 octet)
        """
        print("Scan barcode to get serial no.")  
        scanInput = ''
        if USE_PYNPUT:
            #wait for __on_press() to type new line char to trigger input() capture serial no, after received 12 octet serial no.
            scanInput = input()                                             
        elif USE_KEYBOARD:
            while True:
                event = keyboard.read_event()
                if event.event_type == keyboard.KEY_DOWN:
                    key = event.name
                    if key>='0' and key<='Z':
                        self.barcodeList.append(key)                    
                        if len(self.barcodeList) >= 12:
                            scanInput = ''.join(self.barcodeList)
                            self.barcodeList.clear()
                            break
        else:           
            scanInput = input()

        scanInput = scanInput
        print(f"Read barcode serial no.: {scanInput}\n")  

        macHead = (scanInput[:6]).lower()
        if(macHead!='6ca401'):
            scanInput = False

        return scanInput




