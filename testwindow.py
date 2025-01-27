import tkinter as tk
from tkinter import ttk

# Main window definition, title and dimensions
root = tk.Tk()
root.title("Typ Wars")
#root.geometry("720x480")

# Create a style, and templates that can be used for elements when using said style
style = ttk.Style()
style.configure("M.TLabel", foreground="black", font=('Ariel',25))
style.configure("M.TEntry", foreground="red") # For some reason Entry font can't be declared outside
style.configure("M.TButton", font=('Ariel',25))

# Validation function, to make sure there's no space in the "username" field and restrict to 16 characters
def valuser(newchar, current_string):
    if( " " not in newchar and len(current_string) <= 15 ):
        return True
    else:
        return False
vcmd = root.register(valuser)

# Enter username label and textbox
uname_l = ttk.Label(root, text="Enter username", style="M.TLabel")
uname_l.grid(column=10,row=0)
uname_t = ttk.Entry(root, style="M.TEntry", font=('Ariel',25),  validate='key', validatecommand=(vcmd,"%S","%P")) # %S : Newly entered char, %P : Current full text
enter_b = ttk.Button(text="Enter", style="M.TButton")
quit_b = ttk.Button(text="Quit", style="M.TButton", command=root.destroy)

# Pack everything so that they display on screen
uname_l.pack(pady = 10)
uname_t.pack(padx = 20, pady = 10)
enter_b.pack(pady = 20, padx=20, side=tk.LEFT)
quit_b.pack(pady = 20, padx = 20, side=tk.RIGHT)

# Main window loop
root.mainloop()
