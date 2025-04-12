import mido
import tkinter as tk
import threading
from get_from_reface import get_from_reface
from save_patch import save_patch
from send_patch import send_patch
from config import INPUT_PORT_NAME
import state

# Check if Reface DX is connected
def is_connected():
  try:
    with mido.open_input(INPUT_PORT_NAME):
      return True
  except (OSError, IOError):
    return False

# Use threading to prevent the application from freezing
def run_in_thread(fn, btns):
  def disable_and_run():
    # Disable buttons
    for btn in btns:
      btn.config(state='disabled')
    
    try:
      fn()
    finally:
      for btn in btns:
        btn.config(state='normal')

  thread = threading.Thread(target=disable_and_run)
  thread.daemon = True
  thread.start()

def main():
  root = tk.Tk()
  root.title('Reface DX Library')
  root.geometry('300x300')

  # Connection status label
  connection_status = tk.Canvas(root, width=20, height=20)
  connection_status.pack(pady=5)
  

  # Show current patch's name
  patch_name = tk.Label(root, text='Current patch: no patch loaded')
  patch_name.pack(pady=5)


  # Define buttons
  get_btn = tk.Button(root, text='get patch from reface', height=2, width=25)
  save_btn = tk.Button(root, text='save patch', height=2, width=25, command=save_patch)
  send_btn = tk.Button(root, text='send patch', height=2, width=25)

  # Set run_in_thread commands
  get_btn.config(command=lambda: run_in_thread(get_from_reface, [get_btn, save_btn, send_btn]))
  send_btn.config(command=lambda: run_in_thread(send_patch, [get_btn, save_btn, send_btn]))

  # Place buttons in the application
  get_btn.pack(pady=10)
  save_btn.pack(pady=10)
  send_btn.pack(pady=10)

  last_patch = ['']

  def update_status():
    # Update connection status
    if is_connected():
      connection_status.config(bg='green')
      get_btn.config(state='normal')
      send_btn.config(state='normal')

    else:
      connection_status.config(bg='red')
      get_btn.config(state='disabled')
      send_btn.config(state='disabled')

    # Update loaded patch's name
    if state.current_patch_name != last_patch[0]:
      patch_name.config(text=f"Current patch: {state.current_patch_name}")
      last_patch[0] = state.current_patch_name

    # Enable save button if patch is loaded
    if state.current_patch:
      save_btn.config(state='normal')
    else:
      save_btn.config(state='disabled')

    # Check status every one second
    root.after(1000, update_status)

  update_status()

  root.mainloop()

if __name__ == '__main__':
  main()
