import mido
import tkinter as tk
import threading
import os
from save_patch import save_patch
from load_patch import load_patch
from config import INPUT_PORT_NAME
import state

# Load sysex files from the specified folder
def load_sysex_file_list(listbox, label, change_path=False):
  if change_path:
    # Open a file dialog to select a new folder
    folder_path = tk.filedialog.askdirectory(initialdir='C:/', title='Select folder with SysEx files')
    if folder_path:
      state.syx_folder = folder_path
      label.config(text=state.syx_folder)
  
  listbox.delete(0, tk.END)
  if not os.path.exists(state.syx_folder):
    os.makedirs(state.syx_folder)

  files = [f for f in os.listdir(state.syx_folder) if f.lower().endswith('.syx')]
  files.sort()

  for f in files:
    listbox.insert(tk.END, f)

  # Select the first file in the listbox
  if files:

    # TODO: disable buttons if no files

    listbox.selection_set(0)
    event = tk.Event()
    event.widget = listbox
    on_select_file(event)


# Check if Reface DX is connected
def is_connected():
  try:
    with mido.open_input(INPUT_PORT_NAME):
      return True
  except (OSError, IOError):
    return False

# Use threading to prevent the application from freezing
def run_in_thread(fn, btns, complete=None):
  def disable_and_run():
    # Disable buttons
    for btn in btns:
      btn.config(state='disabled')
    
    try:
      fn()
    finally:
      for btn in btns:
        btn.config(state='normal')
      if complete:
        complete()

  thread = threading.Thread(target=disable_and_run)
  thread.daemon = True
  thread.start()

# Save selected patch name in memory
def on_select_file(event):
  selection = event.widget.curselection()
  if selection:
    index = selection[0]
    filename = event.widget.get(index)
    state.selected_file = filename


def main():
  root = tk.Tk()
  root.title('Reface DX Library')
  root.geometry('300x450')

  main_frame = tk.Frame(root)
  main_frame.pack(fill='both', expand=True)



  # Connection status
  status_frame = tk.Frame(main_frame)
  status_frame.pack(fill='both')

  # TODO: Add a label
  connection_status = tk.Canvas(status_frame, width=20, height=20)
  connection_status.pack(pady=5)



  # Listbox header with patches directory
  listbox_header_frame = tk.Frame(main_frame)
  listbox_header_frame.pack()

  change_path = tk.Button(listbox_header_frame, text='...', height=1, width=2)
  change_path.pack(side='left', fill='y')
  change_path.config(command=lambda: load_sysex_file_list(preset_listbox, current_path_label, True))

  current_path_label = tk.Label(listbox_header_frame, text=state.syx_folder)
  current_path_label.pack(side='right', fill='y')

  # Listbox with saved patches
  listbox_frame = tk.Frame(main_frame)
  listbox_frame.pack()

  preset_listbox = tk.Listbox(listbox_frame, height=20, width=40)
  preset_listbox.pack(side='left', fill='y')

  scrollbar = tk.Scrollbar(listbox_frame, orient='vertical')
  scrollbar.config(command=preset_listbox.yview)
  scrollbar.pack(side='right', fill='y')

  preset_listbox.config(yscrollcommand=scrollbar.set)
  preset_listbox.bind("<<ListboxSelect>>", on_select_file)

  # Buttons
  buttons_frame = tk.Frame(main_frame)
  buttons_frame.pack()

  # Define buttons
  load_btn = tk.Button(buttons_frame, text='LOAD', height=2, width=15)
  save_btn = tk.Button(buttons_frame, text='SAVE', height=2, width=15)


  # Set run_in_thread commands
  load_btn.config(command=lambda: run_in_thread(load_patch, [load_btn, save_btn]))
  save_btn.config(command=lambda: run_in_thread(save_patch, [load_btn, save_btn], lambda: load_sysex_file_list(preset_listbox, current_path_label)))

  # Place buttons in the application
  load_btn.pack(side='left', padx=15, pady=10)
  save_btn.pack(side='right', padx=15, pady=10)


  # Load files on start
  load_sysex_file_list(preset_listbox, current_path_label, not state.syx_folder)

  def update_status():
    # Update connection status
    if is_connected():
      connection_status.config(bg='green')
      load_btn.config(state='normal')
      save_btn.config(state='normal')

    else:
      connection_status.config(bg='red')
      load_btn.config(state='disabled')
      save_btn.config(state='disabled')

    # Check status every one second
    root.after(1000, update_status)

  update_status()

  root.mainloop()

if __name__ == '__main__':
  main()
