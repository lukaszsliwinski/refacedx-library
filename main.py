import mido
import tkinter as tk
import threading
from get_patch import get_patch
from send_patch import send_patch
from config import INPUT_PORT_NAME

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
  root.geometry('300x150')

  # Connection status label
  connection_status = tk.Canvas(root, width=20, height=20)
  connection_status.pack(pady=5)
  
  # Define buttons
  get_btn = tk.Button(root, text='get patch', height=2, width=25)
  send_btn = tk.Button(root, text='send patch', height=2, width=25)

  # Set commands
  get_btn.config(command=lambda: run_in_thread(get_patch, [get_btn, send_btn]))
  send_btn.config(command=lambda: run_in_thread(send_patch, [get_btn, send_btn]))

  # Place button in the application
  get_btn.pack(pady=10)
  send_btn.pack(pady=10)

  # Update connection status
  def update_status():
    if is_connected():
      connection_status.config(bg='green')
      get_btn.config(state='normal')
      send_btn.config(state='normal')

    else:
      connection_status.config(bg='red')
      get_btn.config(state='disabled')
      send_btn.config(state='disabled')

    # Check status every one second
    root.after(1000, update_status)

  update_status()

  root.mainloop()

if __name__ == '__main__':
  main()
