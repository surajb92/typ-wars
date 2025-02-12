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

# ----------------------------------------------
#              GLOBAL STATE MACHINE
# ----------------------------------------------

class globalState:
    # Initialize game state
    def __init__(self):
        self.isServer = False
        self.STATE="START"
        self.userName=''
        self.peerCache = {}
        self.peerIsServer = {}
        self.gLock = threading.Lock()
        self.tempUname=''
        
    # Functions to change game state
    def start_login(self,username):
        with self.gLock:
            self.STATE="LOGGING_IN"
            self.userName=username
    def login_success(self):
        with self.gLock:
            self.STATE="LOGGED_IN"
    def logout(self):
        with self.gLock:
            self.username=''
            self.STATE="START"
            self.isServer=False
    def set_server_state(self,state):
        with self.gLock:
            self.isServer=state
    def add_peer(self,hostname,address):
        with self.gLock:
            self.peerCache[hostname]=address
            if hostname not in self.peerIsServer:
                self.peerIsServer[hostname]=False
            print("Server added!:",hostname,address)
    def remove_peer(self,hostname):
        with self.gLock:
            del self.peerCache[hostname]
            del self.peerIsServer[hostname]
    def update_peer_server_status(self,hostname,status):
        with self.gLock:
            self.peerIsServer[hostname]=status
    # Functions to read game state
    def am_i_server(self):
        with self.gLock:
            return self.isServer
    def get_peer_cache(self):
        with self.gLock:
            return self.peerCache
    def get_username(self):
        with self.gLock:
            return self.userName
    def get_state(self):
        with self.gLock:
            return self.STATE
    def get_peer_server_list(self):
        with self.gLock:
            s_list=[]
            for host,status in self.peerIsServer.items():
                if status:
                    s_list.append(host)
            return s_list

GG=globalState()
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

def quit_program(G):
    G.logout()
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
    
root.protocol('WM_DELETE_WINDOW', lambda: quit_program(GG))

def warning_popup(window, warning_text):
    window.wm_attributes('-type', 'splash')
    tk.messagebox.showinfo(title="Warning!", message=warning_text, icon=tk.messagebox.WARNING)
    window.wm_attributes('-type', 'normal')

# Running as thread from the start
def server_refresh(G):
    print("Refreshing: ",G.get_peer_cache())
    servers=G.get_peer_cache().copy()
    for host,addr in servers.items():
        print("in loop")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test:
            try:
                print('trying to connect to: ',(addr,SERVER_PORT))
                test.connect((addr,SERVER_PORT))
            except Exception as e:
                print("can't connect because : ",e)
                G.remove_peer(h)
                continue
            m="IS_SERVER"
            test.sendall(m.encode())
            reply=test.recv(1024).decode()
            print("reply is server?: ",reply)
            if reply=="YES":
                G.update_peer_server_status(host,True)
            else:
                G.update_peer_server_status(host,False)

# Split from "server_process" thread
def server_process(G,conn,addr):
    print("Entered process")
    msg = conn.recv(1024).decode()
    if msg=="IS_SERVER":
        if G.am_i_server():
            conn.sendall("YES".encode())
        else:
            conn.sendall("NO".encode())

# Running as thread from the start
def server_listener(G):
    #global server_socket
    print("Listening")
    server_socket.listen(5)
    while True:
        try:
            print("Listen found, connecting")
            new_con, new_addr = server_socket.accept()
            print("thread opened")
            # [LATER] Check which type of message comes before opening a thread perhaps.
            threading.Thread(target=server_process,args=(G,new_con,new_addr)).start()
            print("done")
        except Exception as e:
            print("Server Listener is kill",e)
            server_socket.close()
            break

# Running as thread from start
def peer_listener(G):
    while True:
        try:
            data, addr = listener_socket.recvfrom(1024)
        except OSError:
            break
        d=data.decode()
        if d.startswith(MAGIC):
            rec_user = d[len(MAGIC):]
        else:
            continue
        # Delete existing IP if any
        #if addr[0] in G.get_peer_cache() and rec_user=="#@!__EXIT__!@#":
        #        t=list(G.get_peer_cache().keys())[list(G.get_peer_cache().values()).index(addr[0])]
        #        G.remove_peer(t)
        print("rec: ",rec_user)
        
        # Remove peer entry if you get logout shout from peer
        if rec_user=="#@!__EXIT__!@#":
            t=list(G.get_peer_cache().keys())[list(G.get_peer_cache().values()).index(addr[0])] # get hostname of address from which "logout" came
            if t:
                G.remove_peer(t)
        # Check if peer is already in records, process otherwise
        elif rec_user not in G.get_peer_cache():
            # Logged in
            if G.get_state()!="LOGGED_IN":
                peer_shout(G)
                if rec_user != G.get_username():
                    G.add_peer(rec_user,addr[0])
            # Not logged in yet
            else:
                G.add_peer(rec_user,addr[0])

def logout_shout(G):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        s.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, TTL)
        message=MAGIC+"#@!__EXIT__!@#"
        for i in range(0, 200):
            s.sendto(message.encode(), (MCAST_GROUP,PEER_LISTEN_PORT))

def peer_shout(G):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        s.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, TTL)
        message=MAGIC+G.get_username()
        for i in range(0, 200):
            s.sendto(message.encode(), (MCAST_GROUP,PEER_LISTEN_PORT))

# Login function
def login(event,G):
    if not uname_t.get():
        warning_popup(root,"No username entered")
        return
    elif uname_t.get()=="#@!__EXIT__!@#":
        warning_popup(root,"Don't be sneaky now ~ ^_^")
        return
    elif uname_t.get() in G.get_peer_cache():
        warning_popup(root,"User already exists!")
        return
    
    # Set game state for login
    G.start_login(uname_t.get())
    
    # [LATER] If there are already servers in cache, show them while searching maybe?
    
    # Shout your presence on network
    peer_shout(G)
    
    # Set up popup window to urge player to wait while we search for peers
    search_w = tk.Toplevel(root)
    search_w.overrideredirect(True) # Hide titlebar
    tk.Message(search_w, text="Searching for other players...\nPlease wait", anchor='center',padx=20, pady=20).pack()
    center_window(search_w)
    search_w.after(1500, search_w.destroy) # Destroy window after waiting for 1.5 seconds
    
    # search_w.transient(root) # Splash window does not stop tkinter buttons from being clicked without this
    # search_w.wait_visibility() # Some shenanigans with how this works with button command but not with direct bind.. weird..
    search_w.grab_set()
    
    # Completely disables the root window (except movement) until the popup window disappears. Full disable only works on windows, so using this instead.
    root.wm_attributes('-type', 'splash')
    
    # Root will not update and wait here until search_w has been destroyed
    root.wait_window(search_w)
    
    # After 2 seconds of wait -
    root.wm_attributes('-type', 'normal') # Enables window again
    
    # Check peers to update which are in Server mode right now
    server_refresh(G)
       
    # Check whether your username is already taken
    if uname_t.get() in G.get_peer_cache():
        warning_popup(root,"User already exists!")
        G.logout()
        return

    # Login success !
    G.login_success()
    
    loggedin_l.configure(text=loggedin_l.cget("text")+G.get_username())
    if not G.get_peer_server_list():
		# set this system to be server
        #isServer = True
        G.set_server_state(True)
        server_page.pack(fill='both',expand=True)
        root.update()
        center_window(root)
    else:
        #isServer = False
        G.set_server_state(False)
        server_list_page.pack(fill='both',expand=True)
        # TCP connection
    login_page.pack_forget()
    #center_window(root)

def logout(G):
    G.logout()
    logout_shout(G)    
    loggedin_l.configure(text="Logged in as: ")
    server_page.pack_forget()
    server_list_page.pack_forget()
    login_page.pack(fill='both',expand=True)

# [LATER] Will need to revamp with connected peer
def send_message(event,G):
    # now I see the problem with not using classes...
    # ...or do I?
    message_list.configure(state='normal')
    message_list.insert('end',G.get_username()+": "+my_message.get()+'\n')
    message_list.configure(state='disabled')
    my_message.delete(0,'end')

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
listener_thread = threading.Thread(target=peer_listener,args=(GG,))
server_thread = threading.Thread(target=server_listener,args=(GG,))

try:
    listener_socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mreq = socket.inet_aton(MCAST_GROUP) + socket.inet_aton(MY_IP)
    listener_socket.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
    listener_socket.bind(('',PEER_LISTEN_PORT))
    
    server_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
uname_t = ttk.Entry(login_page, style="M.TEntry", font=('Ariel',25), validate='key', validatecommand=(vcmd,"%S","%P")) # %S : Newly entered char, %P : Current full text
enter_b = ttk.Button(login_page, text="Enter", style="M.TButton", command=lambda e=None,g=GG: login(e,g)) # I AM A GENIUS! ...ahem, well that was a nice fix
quit_b = ttk.Button(login_page, text="Quit", style="M.TButton", command=lambda: quit_program(GG))

# Binding Enter key to allow login
# uname_t.bind("<Return>",lambda event,g=GG: login_enter(event,g)) # <-- works as a workaround to use the same old hack...
uname_t.bind("<Return>",lambda e,g=GG: login(e,g)) # ...but this is obviously WAAAY better

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
my_message = ttk.Entry(server_page, font=('Ariel',15))
send_b = ttk.Button(server_page, text="Send", style="S.TButton", command=lambda e=None,g=GG: send_message(e,g))
logout_b = ttk.Button(server_page, text="Logout", style="S.TButton", command=lambda: logout(GG))

# Binding Enter key to allow sending messages
my_message.bind("<Return>",lambda e,g=GG: send_message(e,g))

# Pack Server page items (grid/pack)
# Grid doesn't do autoscaling, so using pack instead.
"""
loggedin_l.grid(row=0, column=0, sticky="news", padx=10, pady=10)
logout_b.grid(row=0, column=2, sticky="ne", padx=10, pady=10)#, columnspan=2)
message_list.grid(row=1, column=0, padx=10, sticky="new",columnspan=10)
message_l.grid(row=2, column=0, sticky="news", padx=10, pady=10)
my_message.grid(row=2, column=1, sticky="news", padx=10, pady=10)
send_b.grid(row=2, column=2, columnspan=2, padx=10, pady=10)
"""
#"""
loggedin_l.pack(padx=10, pady=10, side=tk.LEFT, anchor='nw')
logout_b.pack(pady = 20, padx=20, side=tk.RIGHT, anchor='ne')
message_list.pack(padx=25, pady=25, side=tk.TOP, fill='x')
message_l.pack(pady = 20, padx=20, side=tk.LEFT, anchor='w')
my_message.pack(pady = 20, padx=20, side=tk.LEFT, anchor='n')
send_b.pack(pady = 20, padx=20)#, side=tk.LEFT)
#"""

# 3rd Window : Server List. If there are other users online, display list.
list_l = ttk.Label(server_list_page, text="List of users online: ", style="M.TLabel")
server_list = tk.Text(server_list_page, bg='white')
join_b = ttk.Button(server_list_page, text="Join", style="S.TButton")
logout_b = ttk.Button(server_list_page, text="Logout", style="S.TButton", command=lambda: logout(G))

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
