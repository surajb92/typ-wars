import tkinter as tk
from tkinter import ttk

# Main window definition, title and dimensions
root = tk.Tk()
root.title("Typ Wars")
#root.geometry("720x480") # Setting static dimensions affects dynamic resize, so leave it as is

login_page = ttk.Frame(root)
server_page = ttk.Frame(root)
server_list_page = ttk.Frame(root)

username=tk.StringVar()
messages=tk.StringVar()

# Center the window (not important)
def center_window(window):
    width = root.winfo_width()
    height = root.winfo_height()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")

# Server login function (will need to expand later)
def login():
    username.set(uname_t.get())
    loggedin_l.configure(text=loggedin_l.cget("text")+username.get())

    # ! TEMPORARY ! Use 'client' username to get into Server List page. FOR TESTING PURPOSES ONLY !!!
    if (username.get() == 'client'):
        server_list_page.pack(fill='both',expand=True)
    else:
        server_page.pack(fill='both',expand=True)
    login_page.pack_forget()
    # center_window(root)
# idk what better way to do this, but Enter key function sends 'event' which mouse click doesn't
def login_enter(event):
    login()

def logout():
    loggedin_l.configure(text="Logged in as: ")
    server_page.pack_forget()
    server_list_page.pack_forget()
    login_page.pack(fill='both',expand=True)

def send_message():
    # now I see the problem with not using classes...
    # ...or do I?
    message_list.configure(state='normal')
    message_list.insert('end',username.get()+": "+message_type.get()+'\n')
    message_list.configure(state='disabled')
    message_type.delete(0,'end')
# For enter key
def send_message_enter(event):
    send_message()

# Create a style, and templates that can be used for elements when using said style
style = ttk.Style()
style.configure("M.TLabel", foreground="black", font=('Ariel',25))
style.configure("M.TLabel", foreground="black", font=('Ariel',15))
style.configure("M.TEntry", foreground="red") # For some reason Entry font can't be declared outside
style.configure("M.TButton", font=('Ariel',25))
style.configure("S.TButton", font=('Ariel',15))

# Validation function, to make sure there's no space in the "username" field and restrict to 16 characters
def valuser(newchar, current_string):
    if( " " not in newchar and len(current_string) <= 15 ):
        return True
    else:
        return False
vcmd = root.register(valuser)

# 1st Window : Login. Enter username label and textbox (all rooted to login_page frame)
uname_l = ttk.Label(login_page, text="Enter username", style="M.TLabel")
uname_t = ttk.Entry(login_page, style="M.TEntry", font=('Ariel',25),  validate='key', validatecommand=(vcmd,"%S","%P")) # %S : Newly entered char, %P : Current full text
enter_b = ttk.Button(login_page, text="Enter", style="M.TButton", command=login)
quit_b = ttk.Button(login_page, text="Quit", style="M.TButton", command=root.destroy)

# Binding Enter key to allow login
uname_t.bind("<Return>",login_enter)

# Pack everything so that they display on screen
uname_l.pack(pady = 10)
uname_t.pack(padx = 20, pady = 10)
enter_b.pack(pady = 20, padx=20, side=tk.LEFT)
quit_b.pack(pady = 20, padx = 20, side=tk.RIGHT)

# 2nd Window  : Server Host. If there are no other users online, you will become the host for the chatroom.
loggedin_l = ttk.Label(server_page, text="Logged in as: ", style="M.TLabel")
message_list = tk.Text(server_page, bg='white')
message_list.configure(state='disabled')
message_l = ttk.Label(server_page, text="Enter message: ", style="S.TLabel")
message_type = ttk.Entry(server_page, font=('Ariel',15))
send_b = ttk.Button(server_page, text="Send", style="S.TButton", command=send_message)
logout_b = ttk.Button(server_page, text="Logout", style="S.TButton", command=logout)

# Binding Enter key to allow sending messages
message_type.bind("<Return>",send_message_enter)

# Pack Server page items (grid/pack)
"""
loggedin_l.grid(row=0, column=0, sticky="news", padx=10, pady=10)
logout_b.grid(row=0, column=2, sticky="ne", padx=10, pady=10)#, columnspan=2)
message_list.grid(row=1, column=0, padx=10, sticky="new",columnspan=10)
message_l.grid(row=2, column=0, sticky="news", padx=10, pady=10)
message_type.grid(row=2, column=1, sticky="news", padx=10, pady=10)
send_b.grid(row=2, column=2, columnspan=2, padx=10, pady=10)
"""
#"""
loggedin_l.pack(padx=10, pady=10, side=tk.LEFT, anchor='nw')
logout_b.pack(pady = 20, padx=20, side=tk.RIGHT, anchor='ne')
message_list.pack(padx=25, pady=25, side=tk.TOP, fill='x')
message_l.pack(pady = 20, padx=20, side=tk.LEFT, anchor='w')
message_type.pack(pady = 20, padx=20, side=tk.LEFT, anchor='n')
send_b.pack(pady = 20, padx=20)#, side=tk.LEFT)
#"""

# 3rd Window : Server List. If there are other users online, display list.
list_l = ttk.Label(server_list_page, text="List of users online: ", style="M.TLabel")
server_list = tk.Text(server_list_page, bg='white')
join_b = ttk.Button(server_list_page, text="Join", style="S.TButton")#, command=send_message)
logout_b = ttk.Button(server_list_page, text="Logout", style="S.TButton", command=logout)

# Pack Server List page items
list_l.pack(padx=20, pady=20, side=tk.TOP, anchor='nw')
server_list.pack(padx=10, pady=10, side=tk.TOP, fill='x')
join_b.pack(padx=20, pady=20, side=tk.LEFT, anchor='nw')
logout_b.pack(padx=20, pady=20, side=tk.RIGHT, anchor='nw')

# Display login page
login_page.pack(fill='both',expand=1)

# Main window loop
root.mainloop()
