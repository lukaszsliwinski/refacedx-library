import tkinter as tk
import threading
from get_patch import get_patch
from send_patch import send_patch


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
  root.title("Reface DX Library")
  root.geometry("300x150")

  # Define buttons
  get_btn = tk.Button(root, text="get patch", height=2, width=25)
  send_btn = tk.Button(root, text="send patch", height=2, width=25)

  # Set commands
  get_btn.config(command=lambda: run_in_thread(get_patch, [get_btn, send_btn]))
  send_btn.config(command=lambda: run_in_thread(send_patch, [get_btn, send_btn]))

  # Place button in the application
  get_btn.pack(pady=10)
  send_btn.pack(pady=10)

  root.mainloop()

if __name__ == "__main__":
  main()
