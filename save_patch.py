from tkinter import filedialog
import state

def save_patch():
  print('handle save function')
  if not state.current_patch:
    print('No patch loaded.')
    return

  file_path = filedialog.asksaveasfilename(
    defaultextension='.syx',
    filetypes=[('SysEx files', '*.syx')],
    title='Zapisz patch jako...'
  )

  if file_path:
    with open(file_path, 'wb') as f:
      for msg in state.current_patch:
        f.write(bytes([0xF0] + list(msg.data) + [0xF7]))
    print(f'Patch saved in : {file_path}')
