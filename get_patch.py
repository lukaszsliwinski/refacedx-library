import mido
import time
from config import INPUT_PORT_NAME, OUTPUT_PORT_NAME, TIMEOUT, DELAY, DUMP_REQUEST

def get_patch():
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

    print('Patch received and saved.')
    # TODO: .txt
