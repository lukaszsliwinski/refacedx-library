import mido
import time
from tkinter import filedialog
from config import INPUT_PORT_NAME, OUTPUT_PORT_NAME, TIMEOUT, DELAY, DUMP_REQUEST

def save_patch():
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

    if not sysex_data:
      print('No patch loaded.')
      return

    file_path = filedialog.asksaveasfilename(
      defaultextension='.syx',
      filetypes=[('SysEx files', '*.syx')],
      title='Save patch as...',
      initialfile=name.strip().lower()
    )

    if file_path:
      with open(file_path, 'wb') as f:
        for msg in sysex_data:
          f.write(bytes([0xF0] + list(msg.data) + [0xF7]))
      print(f'Patch saved in : {file_path}')
