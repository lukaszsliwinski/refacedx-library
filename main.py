import tkinter as tk
from get_patch import get_patch
from send_patch import send_patch

def main():
  root = tk.Tk()
  root.title("Reface DX Library")
  root.geometry("300x150")

  tk.Button(root, text="get patch", command=get_patch, height=2, width=25).pack(pady=10)
  tk.Button(root, text="send patch", command=send_patch, height=2, width=25).pack(pady=10)

  root.mainloop()

if __name__ == "__main__":
  main()
