import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import asyncio
import socket

# Main window definition, title and dimensions
root = tk.Tk()
root.title("Typ Wars")
#root.geometry("720x480") # Setting static dimensions affects dynamic resize, so leave it as is

# Function to get local IP
def get_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as ipsock:
        ipsock.connect(("8.8.8.8",1))
        return ipsock.getsockname()[0]

# GUI variables
login_page = ttk.Frame(root)
server_page = ttk.Frame(root)
server_list_page = ttk.Frame(root)

# Message app variables
isServer = False
username=tk.StringVar()
messages=tk.StringVar()

# Network variables
MY_IP = get_ip()
MCAST_GROUP = "224.1.1.251"
MAGIC = "!@#typ_wars#@!"
PEER_LISTEN_PORT=3003
PORT=3000
TTL=2
server_cache = {}

# Status variables
logging_in = False
logged_in = False
in_game = False


# Center the window
def center_window(window):
    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    #print("width: ",width,"height: ",height,"x: ",x,"y: ",y)
    window.geometry(f"{width}x{height}+{x}+{y}")
    #window.geometry(f"+{x}+{y}")

""" Frame disable enable : Not required as of now, but keeping in case needed in the future.
def disable_frame(parent):
    for child in parent.winfo_children():
        wtype = child.winfo_class()
        if wtype not in ('Frame','Labelframe','TFrame','TLabelframe'):
            child.configure(state='disable')
        else:
            disableChildren(child)

def enable_frame(parent):
    for child in parent.winfo_children():
        wtype = child.winfo_class()
        if wtype not in ('Frame','Labelframe','TFrame','TLabelframe'):
            child.configure(state='normal')
        else:
            enableChildren(child)
"""

async def check_duplicate_peer(u):
    notdupe=True
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as p:
        p.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Disable after local testing
        mreq = socket.inet_aton(MCAST_GROUP) + socket.inet_aton(MY_IP)
        p.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        p.bind(('',PEER_LISTEN_PORT))
        # This is a problem
        while notdupe:
            data, addr = await p.recvfrom(1024)
            if logging_in:
                d=data.decode()
                if (d.startswith(MAGIC)):
                    if(d == username.get()):
                        notdupe=False
                    elif(d not in server_cache):
                        server_cache.append(d,addr[0])
            else:
                break
    return notdupe

async def peer_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as l:
        l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Disable after local testing
        mreq = socket.inet_aton(MCAST_GROUP) + socket.inet_aton(MY_IP)
        l.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        l.bind(('',PEER_LISTEN_PORT))
        while True:
            await(data, addr = l.recvfrom(1024))
            if logged_in:
                d=data.decode()
                if (d.startswith(MAGIC) and d not in server_cache and d != username.get()):
                    server_cache.append(d,addr[0])
            else:
                break

async def peer_shout():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Disable after local testing
        s.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, TTL)
        for i in range(0, 200):
            s.sendto(username.get().encode(), (MCAST_GROUP,PEER_LISTEN_PORT))

# Server login function (will need to expand later)
def login():
    logging_in=True
    
    # Shout your presence on network
    asyncio.run(peer_shout())
    asyncio.run(peer_listener())
    
    # [LATER] If there are already servers in cache, show them while searching maybe?
    
    # Set up popup window to urge player to wait while we search for peers
    search_w = tk.Toplevel(root)
    search_w.overrideredirect(True) # Hide titlebar
    tk.Message(search_w, text="Searching for other players...\nPlease wait", anchor='center',padx=20, pady=20).pack()
    center_window(search_w)
    search_w.after(1500, search_w.destroy) # Destroy window after waiting for 1.5 seconds
    
    # These commands disable the root window until the popup window disappears
    root.wm_attributes('-type', 'splash') # Completely disables root window, except moving it. Full disable only works on windows, so using this instead.
    
    # root.withdraw() # Completely hides/shows the window. Risky if there's any error, app will hang.
    # root.deiconify()
    
    # disable_frame(login_page) # Disables all the children, can work with a custom titlebar, but not without it
    # enable_frame(login_page)
    
    # search_w.transient(root) # Splash window seems to do the job of these 2 already, but keeping in case I missed some interaction
    # search_w.grab_set()
    
    # Check for other hosts & whether your username is already taken
    # dupe = asyncio.run(check_duplicate_peer(username.get()))
    
    # Root will not update and wait here until search_w has been destroyed
    root.wait_window(search_w)

    # After 2 seconds of wait -
    root.wm_attributes('-type', 'normal') # Enables window again
    
    # If duplicate user already exists, stop login
    if dupe:
        root.wm_attributes('-type', 'splash')
        tk.messagebox.showinfo(title="Warning!", message="User already exists!")
        root.wm_attributes('-type', 'normal')
        logging_in = False
        return
   
    # Login success !
    logging_in = False
    logged_in = True
    username.set(uname_t.get())
    loggedin_l.configure(text=loggedin_l.cget("text")+username.get())
    if not server_cache:
		# set this system to be server
        isServer = True
        server_page.pack(fill='both',expand=True)
        # Set up listener to listen to presence of other hosts
        #asyncio.run(peer_listener())
        center_window(root)
    else:
        isServer = False
        server_list_page.pack(fill='both',expand=True)
        # TCP connection
    login_page.pack_forget()
    #center_window(root)
    
# idk what better way to do this, but Enter key function sends 'event' which mouse click doesn't
def login_enter(event):
    login()

def logout():
    logged_in=False
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
# For handling messages sent with enter key
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
# Grid doesn't do autoscaling, so using pack instead.
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
