import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import socket
import threading
import select

# Main window definition, title and dimensions
root = tk.Tk()
root.title("Typ Wars")
#root.geometry("720x480") # Setting static dimensions affects dynamic resize, so leave it as is

class globalState:
    truth=True
    def isTruth():
        return truth

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
SERVER_PORT=3000
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
    #window.geometry(f"{width}x{height}+{x}+{y}")
    window.geometry(f"+{x}+{y}")

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

def quit_program():
    global logging_in,logged_in,listener_socket,server_socket
    logging_in=False
    logged_in=False
    try:
        listener_socket.shutdown(socket.SHUT_RDWR)
    except Exception as e:
        listener_socket.close()
    server_socket.shutdown(socket.SHUT_RDWR)
    try:
        listener_thread.join()
        server_thread.join()
    except Exception as e:
        print("Error closing threads: ",e)
    root.destroy()
    
root.protocol('WM_DELETE_WINDOW', quit_program)

def warning_popup(window, warning_text):
    window.wm_attributes('-type', 'splash')
    tk.messagebox.showinfo(title="Warning!", message=warning_text, icon=tk.messagebox.WARNING)
    window.wm_attributes('-type', 'normal')

# Running as thread from the start
def server_refresh():
    global server_cache
    with lis_lock:
        print("Refreshing: ",server_cache)
        for h in server_cache.copy():
            print("in loop")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test:
                #test.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                #test.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                test.settimeout(1) # temp solution, connect is still not working
                try:
                    print('trying to connect to: ',(server_cache[h],SERVER_PORT))
                    test.connect((server_cache[h],SERVER_PORT))
                    #test.connect(("8.8.8.8",3001))
                except Exception as e:
                    print("EXCEPTION! > ",e)
                    del server_cache[h]
                    continue
                m="IS_SERVER"
                test.sendall(m.encode())
                reply=test.recv(1024).decode()
                print("reply is server?: ",reply)
                if reply!="YES":
                    del server_cache[h]

# Split from "server_process" thread
def server_process(conn,addr):
    global isServer
    print("Entered process")
    msg = conn.recv(1024).decode()
    if msg=="IS_SERVER":
        if isServer:
            conn.sendall("YES".encode())
        else:
            conn.sendall("NO".encode())
    #elif msg=="CONNECT": # Game data exchange here ??? REALLY ?!?! Might need to start a new thread
    #    pass

# Running as thread from the start
def server_listener():
    global server_socket
    print("Listening")
    server_socket.listen(5)
    while server_socket:
        try:
            print("Listen found, connecting")
            new_con, new_addr = server_socket.accept()
            print("thread opened")
            threading.Thread(target=server_process,args=(new_con,new_addr)).start()
            print("done")
        except OSError:
            print("Connection error")
            break
        except Exception as e:
            print("inside listener thread: ",e)

# Running as thread from start
def peer_listener():
    global server_cache,logging_in,username
    while listener_socket:
        try:
            data, addr = listener_socket.recvfrom(1024)
        except OSError:
            break
        with lis_lock:
            d=data.decode()
            if d.startswith(MAGIC):
                rec_user = d[len(MAGIC):]
            else:
                continue
            # Delete existing IP if any
            if addr[0] in server_cache.values():
                t=list(server_cache.keys())[list(server_cache.values()).index(addr[0])]
                del server_cache[t]
            # Only do ops if this is not a peer in our records
            if rec_user not in server_cache:
                # Not logged in with our username yet
                if not username.get() or logging_in:
                    server_cache[rec_user]=addr[0]
                # Logged in, username claimed
                else:
                    peer_shout()
                    if rec_user != username.get():
                        server_cache[rec_user]=addr[0]

def peer_shout():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        s.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, TTL)
        message=MAGIC+username.get()
        for i in range(0, 200):
            s.sendto(message.encode(), (MCAST_GROUP,PEER_LISTEN_PORT))

# Server login function (will need to expand later)
def login():
    # Globals are a PITA, I get it, but I'll have to work with them for now
    # Maybe do global state class as the next step? idk how to push that onto tkinter functions though...
    # Live and learn?
    global logging_in,logged_in,username,isServer,root,server_cache
    
    with lis_lock:
        logging_in=True
        username.set(uname_t.get())
        
    if not username.get():
        warning_popup(root,"No username entered")
        return
    
    # [LATER] If there are already servers in cache, show them while searching maybe?
    server_refresh()
    if username.get() in server_cache:
        warning_popup(root,"User already exists!")
        return
        
    # Shout your presence on network
    peer_shout()
    
    # Set up popup window to urge player to wait while we search for peers
    search_w = tk.Toplevel(root)
    search_w.overrideredirect(True) # Hide titlebar
    tk.Message(search_w, text="Searching for other players...\nPlease wait", anchor='center',padx=20, pady=20).pack()
    center_window(search_w)
    search_w.after(1500, search_w.destroy) # Destroy window after waiting for 1.5 seconds
    
    # Completely disables the root window (except movement) until the popup window disappears. Full disable only works on windows, so using this instead.
    root.wm_attributes('-type', 'splash')
    
    # search_w.transient(root) # Splash window does not stop tkinter buttons from being clicked without this
    search_w.grab_set()
    
    # Root will not update and wait here until search_w has been destroyed
    root.wait_window(search_w)
    
    # After 2 seconds of wait -
    root.wm_attributes('-type', 'normal') # Enables window again
    
    server_refresh()
    
    # [LATER] Check all servers in cache for alive status (TCP)
    
    # Check whether your username is already taken
    if username.get() in server_cache:
        with lis_lock:
            logging_in = False
        warning_popup(root,"User already exists!")
        return

    # Login success !
    logging_in = False
    logged_in = True
    
    loggedin_l.configure(text=loggedin_l.cget("text")+username.get())
    if not server_cache:
		# set this system to be server
        isServer = True
        server_page.pack(fill='both',expand=True)
        root.update()
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
    global logged_in,isServer
    with lis_lock:
        logged_in=False
        isServer=False
        username.set('')
    loggedin_l.configure(text="Logged in as: ")
    server_page.pack_forget()
    server_list_page.pack_forget()
    login_page.pack(fill='both',expand=True)

# [LATER] Will need to revamp with connected peer
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

# tk validation function, to make sure there's no spaces in the "username" field and restrict to 16 characters
def valuser(newchar, current_string):
    if( ' ' not in newchar and len(current_string) <= 15 ):
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
server_thread = threading.Thread(target=server_listener)
lis_lock = threading.Lock()

try:
    listener_socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Disable after local testing
    mreq = socket.inet_aton(MCAST_GROUP) + socket.inet_aton(MY_IP)
    listener_socket.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
    listener_socket.bind(('',PEER_LISTEN_PORT))
    
    server_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    server_socket.bind((MY_IP,SERVER_PORT))
except Exception as e:
    print("Error creating sockets: ",e)
    sys.exit(1)

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
    # Start threads
    listener_thread.start()
    server_thread.start()
    # Display login page
    login_page.pack(fill='both',expand=1)
    root.mainloop()

# Script import protection
if __name__ == '__main__':
    main()
