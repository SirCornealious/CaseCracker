# Save as test_tkinter.py
import tkinter as tk
from tkinter import ttk
root = tk.Tk()
root.title("Test")
root.geometry("400x300")
notebook = ttk.Notebook(root)
notebook.pack()
frame1 = ttk.Frame(notebook)
notebook.add(frame1, text="Tab 1")
ttk.Label(frame1, text="Test tab").pack()
ttk.Button(frame1, text="Close", command=root.quit).pack()
root.mainloop()
print("GUI closed")