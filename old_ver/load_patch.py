import rtmidi
import time
from config import OUTPUT_PORT_NAME, DELAY
import state

def load_patch():
  # MIDI port initialization
  midiout = rtmidi.MidiOut()
  ports = midiout.get_ports()
  print('Available MIDI ports:')
  for i, port in enumerate(ports):
    print(f'{i}: {port}')
  outport_idx = next((i for i, name in enumerate(ports) if name == OUTPUT_PORT_NAME), None)

  try:
    midiout.open_port(outport_idx)
  except RuntimeError:
    print('Port for Reface DX not found.')  

  # Read .syx file
  with open(f'{state.syx_folder}/{state.selected_file}', 'rb') as f:
    data = list(f.read())

  i = 0
  while i < len(data):
    if data[i] == 0xF0:
      try:
        # Extract partial sysex
        end = data.index(0xF7, i)
        sysex = data[i:end + 1]

        # Send partial sysex and wait before another
        if sysex[0] == 0xF0 and sysex[-1] == 0xF7:
          midiout.send_message(sysex)
          time.sleep(DELAY)
        else:
          print('Incomplete SysEx message.')

        i = end + 1
      except ValueError:
        print('No end (0xF7) for SysEx message.')
        break
    else:
      i += 1

  midiout.close_port()
  print('Patch sent to Reface DX.')
