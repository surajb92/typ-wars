import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import asyncio
import socket
import threading
import select

# Main window definition, title and dimensions
root = tk.Tk()
root.title("Typ Wars")
#root.geometry("720x480") # Setting static dimensions affects dynamic resize, so leave it as is

# ----------------------------------------------
#                   NETWORKING 
# ----------------------------------------------

# Function to get local IP
def get_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as ipsock:
        ipsock.connect(("8.8.8.8",1))
        return ipsock.getsockname()[0]
MY_IP = get_ip()
MCAST_GROUP = "224.1.1.251"
MAGIC = "!@#typ_wars#@!"
PEER_LISTEN_PORT=3003
PORT=3000
TTL=2

# ----------------------------------------------
#                   FUNCTIONS 
# ----------------------------------------------
        
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

lis = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def close_listener():    
    try:
        listener_socket.shutdown(socket.SHUT_RDWR)
    except OSError:
        listener_socket.close()

def quit_program():
    logging_in=False
    logged_in=False
    close_listener()
    root.destroy()
root.protocol('WM_DELETE_WINDOW', quit_program)

def does_username_exist():
    d=False
    if username.get() in server_cache:
        #pop(username.get())
        d=True
    return d

def peer_listener():
    global server_cache
    print("inside: ",listener_socket)
    i=0
    #global logging_in
    while listener_socket:
        #print("blocking at recv")
        data, addr = listener_socket.recvfrom(1024)
        d=data.decode()
        if not d:
            print("dead thread")
            print("Serv: ",server_cache)
            break
        elif d.startswith(MAGIC):
            rec_user = d[len(MAGIC):]
        else:
            continue
        #peer_shout()
        #print("received data")
        i+=1
        #print("logging in: ",i,": ",logging_in)
        if rec_user not in server_cache:
            #print("not in cache")
            if rec_user == username.get():
                #print("same uname")
                global logging_in
                print("logging in: ",logging_in)
                if logging_in:
                    print("logging in")
                    server_cache[rec_user]=addr[0]
            else:
                server_cache[rec_user]=addr[0]
        print("Serv: ",server_cache)
        """
        if rec_user not in server_cache:
            
            print("added")
            print("d: ",d[len(MAGIC):],"username: ",username.get())
            if d.startswith(MAGIC) != username.get():
                if logging_in:
                    server_cache[d]=addr[0]
                print("uhh don't?")
            elif logged_in:
                peer_shout() # Tell the other guy who's boss
                # ^ Watch for this causing lag later on, might need to thread it if it causes problems
                continue
            elif logging_in:
                server_cache[d]=addr[0]
        """
def peer_shout():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Disable after local testing
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0) # <--- [CURRENT]
        s.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, TTL)
        message=MAGIC+username.get()
        for i in range(0, 200):
            s.sendto(message.encode(), (MCAST_GROUP,PEER_LISTEN_PORT))
#shout_thread = threading.Thread(peer_shout,None)

# Server login function (will need to expand later)
def login():
    logging_in=True
    username.set(uname_t.get())
        
    if not username.get():
        # [LATER] Do a proper popup here
        print("No username entered")
        return
    
    #asyncio.run(peer_listener())
    #async with asyncio.TaskGroup() as tg:
    #    tg.create_task(peer_shout())
    #    tg.peer_listener(peer_listener())
    
    # Shout your presence on network
    peer_shout()
    
    # [LATER] If there are already servers in cache, show them while searching maybe?
    
    # Set up popup window to urge player to wait while we search for peers
    search_w = tk.Toplevel(root)
    search_w.overrideredirect(True) # Hide titlebar
    tk.Message(search_w, text="Searching for other players...\nPlease wait", anchor='center',padx=20, pady=20).pack()
    center_window(search_w)
    search_w.after(1500, search_w.destroy) # Destroy window after waiting for 1.5 seconds
    
    # Completely disables the root window (except movement) until the popup window disappears. Full disable only works on windows, so using this instead.
    root.wm_attributes('-type', 'splash')
    
    # disable_frame(login_page) # Disables all the children, can work with a custom titlebar, but not without it
    # enable_frame(login_page)
    
    # search_w.transient(root) # Splash window seems to do the job of these 2 already, but keeping in case I missed some interaction
    # search_w.grab_set()
    
    # Root will not update and wait here until search_w has been destroyed
    root.wait_window(search_w)
    
    # After 2 seconds of wait -
    root.wm_attributes('-type', 'normal') # Enables window again
    
    print(server_cache)
    
    # Check whether your username is already taken
    dupe = does_username_exist()
    # If duplicate user already exists, stop login
    if dupe:
        print("dupe")
        root.wm_attributes('-type', 'splash')
        tk.messagebox.showinfo(title="Warning!", message="User already exists!")
        root.wm_attributes('-type', 'normal')
        logging_in = False
        #server_cache.pop(username.get())
        return
   
    # Login success !
    logging_in = False
    logged_in = True
    
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

# ----------------------------------------------
#                   VARIABLES
# ----------------------------------------------

# GUI variables
login_page = ttk.Frame(root)
server_page = ttk.Frame(root)
server_list_page = ttk.Frame(root)

# Message app variables
server_cache = {}
username=tk.StringVar()
messages=tk.StringVar()

# Network variables
listener_thread = threading.Thread(target=peer_listener)

try:
    listener_socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Disable after local testing
    mreq = socket.inet_aton(MCAST_GROUP) + socket.inet_aton(MY_IP)
    listener_socket.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
    listener_socket.bind(('',PEER_LISTEN_PORT))
    #listener_socket.setsockopt(socket.block
    #print("what the fuck: ",listener_socket.getblocking())
except Exception as e:
    print("Error creating socket: ",e)
    sys.exit(1)
print("outside: ",listener_socket)

# Status variables
isServer = False
logging_in = False
logged_in = False
in_game = False

# 1st Window : Login. Enter username label and textbox (all rooted to login_page frame)
uname_l = ttk.Label(login_page, text="Enter username", style="M.TLabel")
uname_t = ttk.Entry(login_page, style="M.TEntry", font=('Ariel',25),  validate='key', validatecommand=(vcmd,"%S","%P")) # %S : Newly entered char, %P : Current full text
enter_b = ttk.Button(login_page, text="Enter", style="M.TButton", command=login)
quit_b = ttk.Button(login_page, text="Quit", style="M.TButton", command=quit_program)

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

# Main window loop
def main():
    # Start listener thread for other clients
    listener_thread.start()
    # Display login page
    login_page.pack(fill='both',expand=1)
    root.mainloop()

# Script import protection
if __name__ == '__main__':
    # asyncio.run(main())
    main()
