import mido
import time
from config import INPUT_PORT_NAME, OUTPUT_PORT_NAME, TIMEOUT, DELAY, DUMP_REQUEST
import state

def get_from_reface():
  # Open MIDI ports
  with mido.open_input(INPUT_PORT_NAME) as inport, mido.open_output(OUTPUT_PORT_NAME) as outport:
    # Send dump request
    msg = mido.Message('sysex', data=DUMP_REQUEST)
    outport.send(msg)

    # Recieve bulk dump
    start_time = time.time()
    sysex_data = []
    name = ''

    while time.time() - start_time < TIMEOUT:
      for i, msg in enumerate(inport.iter_pending()):
        if msg.type == 'sysex':
          sysex_data.append(msg)

          # Get patch name
          if i == 1:
            for j in range(10,20):
              name += chr(msg.data[j])

      time.sleep(DELAY)

    if not sysex_data:
      raise TimeoutError('No SysEx response')
    
    # Store patch data in apps memory
    state.current_patch = sysex_data
    state.current_patch_name = name
    print(f'{name} patch received and saved in memory (RAM).')
