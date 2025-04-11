import mido
import time

# Global variables for MIDI ports
# TODO: move to config file
INPUT_PORT_NAME = 'reface DX 0'
OUTPUT_PORT_NAME = 'reface DX 1'

TIMEOUT = 2
DELAY = 0.1

# Dump request for reface DX (from documentation)
DUMP_REQUEST = [
    0x43,       # Yamaha ID
    0x20,       # Device Number
    0x7F,       # Group Number High
    0x1C,       # Group Number Low
    0x05,       # Model ID
    0x0E,       # Address High (VOICE Bulk Header)
    0x0F,       # Address Mid (VOICE Bulk Header)
    0x00        # Address Low (VOICE Bulk Header)
]

def main():
  # Open MIDI ports
  with mido.open_input(INPUT_PORT_NAME) as inport, mido.open_output(OUTPUT_PORT_NAME) as outport:
    # Send dump request
    msg = mido.Message('sysex', data=DUMP_REQUEST)
    outport.send(msg)

    # Recieve bulk dump
    start_time = time.time()
    sysex_data = []

    while time.time() - start_time < TIMEOUT:
      for msg in inport.iter_pending():
        if msg.type == 'sysex':
          sysex_data.append(msg)
      time.sleep(DELAY)

    if not sysex_data:
      raise TimeoutError('No SysEx response')

    # TODO: patch name from input in GUI
    with open('dx_patch.syx', 'wb') as f:
      for msg in sysex_data:
        f.write(bytes([0xF0] + list(msg.data) + [0xF7]))

    # TODO: .txt

if __name__ == '__main__':
  main()
