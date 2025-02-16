import tkinter as tk
#import tkinter.simpledialog
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk
import socket
import threading
import time

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
        self.threadz=True
        
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
            dbg("Server added!:",hostname,address)
    def remove_peer(self,hostname):
        with self.gLock:
            del self.peerCache[hostname]
            del self.peerIsServer[hostname]
    def update_peer_server_status(self,hostname,status):
        with self.gLock:
            self.peerIsServer[hostname]=status
    def start_game(self):
        with self.gLock:
            self.STATE="IN_GAME"
    def exit_game(self):
        with self.gLock:
            self.username=''
            self.STATE="START"
            self.isServer=False
            self.threadz=False

    # Functions to read game state
    def get_app_status(self):
        with self.gLock:
            return self.threadz
    def am_i_server(self):
        with self.gLock:
            return self.isServer
    def get_peer_cache(self):
        with self.gLock:
            # Basically, __TEMP__ addresses are created for peers with same hostname to avoid peer_shout loop in udp_peer_listener, and will usually get
            # deleted immediately after the peer sends logout_shout. This "if" is there to handle any micro issues that may arise due to
            # referencing peerCache while those placeholder addresses are still present in it.
            if "__TEMP__" in self.peerCache.values():
                for h,a in self.peerCache.copy().items():
                    if a=="__TEMP__":
                        del self.peerCache[h]
            return self.peerCache
    def get_peer_cache_UNCLEAN_DO_NOT_USE(self): # My clever "solution" just causes the loop again...
        with self.gLock:
            return self.peerCache # This is a bandaid fix which will likely be permanent, PLEASE do not use this function outside udp_peer_listener !
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

class gameState:
    def __init__(self,area,field):
        self.goodWords = [] # list of acceptable words.. move file opening here?
        self.screenWords = {} # list of words on screen
        self.spawnArea = 100
        self.screenLimit = 20
        self.wordCount = 0
        self.difficulty = 0.5
        self.screen=area
        self.textField = field
        self.textField.bind("<Return>", lambda e: self.word_entered(e) )
    def spawn_word(self,word):
        if word in self.screenWords:
            dbg("duplicate word on screen")
        if self.wordCount < self.screenLimit:
            t=self.screen.create_text(self.spawnArea,50,text=word,fill="#FFFFFF",font=("Arial",20))
            self.spawnArea += 200
            if self.spawnArea > 1300:
                self.spawnArea=100
            self.screenWords[word]=t
            self.wordCount+=1
    def word_entered(self,event):
        # if word in words: # verify if word is a dictionary word
        word=self.textField.get()
        self.textField.delete(0,'end')
        dbg("Enter success")
        dbg("List: ",self.screenWords)
        dbg("Word: ",word)
        if word in self.screenWords:
            dbg("If success")
            self.screen.delete(self.screenWords[word])
            del self.screenWords[word]
    def update(self):
        for i in self.screenWords:
            self.screen.move(self.screenWords[i],0,10)
    def get_difficulty(self):
        return self.difficulty

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
PEER_LISTEN_PORT=3001
SERVER_PORT=3002
TTL=2

# ----------------------------------------------
#                   FUNCTIONS 
# ----------------------------------------------

# For debugging
def dbg(*args,d=0):
    if d==0:
        print(*args) # Remove for production
    else:
        # These are exceptions, log these into file or smth later on, for now just print
        print("DebugLine: ")
        print(*args)

# Center the window
def center_window(window):
    window.update()
    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    #dbg("width: ",width,"height: ",height,"x: ",x,"y: ",y)
    #window.update()
    window.geometry(f"{width}x{height}+{x}+{y}")
    #window.geometry(f"+{x}+{y}")

def quit_program(G):
    logout_shout(G)
    G.exit_game()
    #try:
    #    udp_listener_socket.shutdown(socket.SHUT_RDWR)
    #except Exception as e:
    #    udp_listener_socket.close()
    #tcp_listener_socket.shutdown(socket.SHUT_RDWR)
    try:
        udp_listener_thread.join()
        tcp_listener_thread.join()
    except Exception as e:
        dbg("Error closing listener threads: ",e,d=1)
    root.destroy()
    
root.protocol('WM_DELETE_WINDOW', lambda: quit_program(GG))

def warning_popup(window, warning_text):
    window.wm_attributes('-type', 'splash')
    tk.messagebox.showwarning(title="Warning!", message=warning_text) #, icon=tk.messagebox.WARNING)
    window.wm_attributes('-type', 'normal')

# Inform a peer that I am a server now
def server_inform(addr):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test:
        try:
            test.connect((addr,SERVER_PORT))
        except Exception as e:
            return
        test.sendall("IM_SERVER".encode())

# Check if a peer is a server
def server_ping(addr):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test:
        try:
            dbg('trying to connect to: ',(addr,SERVER_PORT))
            test.connect((addr,SERVER_PORT))
        except Exception as e:
            dbg("Unable to ping server: ",e,d=1)
            return False
        m="IS_SERVER"
        test.sendall(m.encode())
        reply=test.recv(1024).decode()
        dbg("How fast?: ",reply)
        if reply=="YES":
            return True
        else:
            return False

# Refresh list of servers <-- might not be needed if everything runs well. Try a flowchart.
def server_refresh(G):
    servers=G.get_peer_cache().copy()
    for host,addr in servers.items():
        G.update_peer_server_status(host,server_ping(addr))

# Split from "server_process" thread
def server_process(G,conn,addr):
    dbg("waiting to receive")
    #dbg("waiting to receive")
    msg = conn.recv(1024).decode()
    dbg("received")
    if msg=="IS_SERVER":
        if G.am_i_server():
            conn.sendall("YES".encode())
        else:
            conn.sendall("NO".encode())
        dbg("sent")
    elif msg=="IM_SERVER":
        t=list(G.get_peer_cache().keys())[list(G.get_peer_cache().values()).index(addr[0])]
        G.update_peer_server_status(t,True)
        server_display_refresh(G)
    # [LATER] Main gameloop will most likely be in an elif here... gonna be weird

# Running as thread from the start
def tcp_peer_listener(G):
    tcp_listener_socket.listen(5)
    while G.get_app_status():
        try:
            new_con, new_addr = tcp_listener_socket.accept()
            dbg("spinning thread")
            threading.Thread(target=server_process,args=(G,new_con,new_addr)).start()
            # [FIX NEEDED] -> Handle regular queries within this loop itself, so that only one ?
        except TimeoutError:
            continue
        except Exception as e:
            dbg("TCP Listener is kill: ",e,d=1)
            tcp_listener_socket.close()
            break

def server_display_refresh(G):
    server_list.delete(0,tk.END)
    j=1
    dbg("Refreshing servers: ", G.get_peer_server_list())
    for i in G.get_peer_server_list():
        server_list.insert(j, i)
        j+=1

# Running as thread from start
def udp_peer_listener(G):
    while G.get_app_status():
        try:
            data, addr = udp_listener_socket.recvfrom(1024)
        except TimeoutError:
            continue
        except Exception as e:
            dbg("UDP Listener is kill.",e,d=1)
            break
        d=data.decode()
        if d.startswith(MAGIC):
            rec_user = d[len(MAGIC):]
        else:
            continue
                    
        # --> RECV (EXIT MESSAGE)
        # Remove peer entry if you get logout shout from peer
        if rec_user=="#@!__EXIT__!@#":
            if addr[0] in G.get_peer_cache().values():
                t=list(G.get_peer_cache().keys())[list(G.get_peer_cache().values()).index(addr[0])] # get hostname of address from which "logout" came
                G.remove_peer(t)
                server_display_refresh(G)
        # --> RECV (USERNAME UDP PEER SHOUT)
        # Check if peer is already in records, process otherwise
        elif rec_user not in G.get_peer_cache_UNCLEAN_DO_NOT_USE(): # Using unclean get ONLY HERE, to avoid peer_shout loop
            # I'm logged in
            if G.get_state()=="LOGGED_IN":
                dbg("Logged in")
                if rec_user != G.get_username():
                    dbg("not same uname, so adding")
                    G.add_peer(rec_user,addr[0])
                else:
                    G.add_peer(rec_user,"__TEMP__") # Placeholder for duplicate username, will usually be deleted immediately. Avoids peer_shout loop.
                # <-- SEND (PEER SHOUT)
                peer_shout(G)
            # I'm not logged in yet
            else:
                G.add_peer(rec_user,addr[0]) # server_ping(addr[0]))
                dbg("not logged in, so adding")

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
        dbg("shout done")

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
    
    G.start_login(uname_t.get()) # Set game state for login
    root.focus_set() # This is to prevent repeated "Enter" keypresses from Entry widget from calling "login" function multiple times
    peer_shout(G) # Shout your presence on network

    search_w = tk.Toplevel(root) # Set up popup window to urge player to wait while we search for peers
    search_w.overrideredirect(True) # Hide titlebar
    tk.Message(search_w, text="Searching for other players...\nPlease wait", anchor='center',padx=20, pady=20).pack()
    center_window(search_w)
    search_w.after(700, search_w.destroy) # Destroy window after waiting for 700ms
    
    # search_w.wait_visibility() # Some shenanigans with how this works with button command but not with direct bind.. weird.. (seems fixed now though)
    search_w.grab_set() # Splash window does not stop tkinter buttons from being clicked without this
    # Completely disables the root window (except movement) until the popup window disappears. Full disable only works on windows, so using this instead.
    root.wm_attributes('-type', 'splash')
    # Root will not update and wait here until search_w has been destroyed
    root.wait_window(search_w)
    
    # After 700ms wait -
    root.wm_attributes('-type', 'normal') # Enables window again
    
    # Check peers to update which are in Server mode right now
    server_refresh(G)
        
    # Check whether your username is already taken
    if uname_t.get() in G.get_peer_cache():
        logout(G)
        warning_popup(root,"User already exists!")
        return

    G.login_success()    
    loggedin_l.configure(text=loggedin_l.cget("text")+G.get_username())
    if not G.get_peer_server_list():
		# If there's no other server online, set this system to be server
        G.set_server_state(True)
        for addr in G.get_peer_cache().values():
            server_inform(addr)
        server_page.pack(fill='both',expand=True)
        center_window(root)
        my_message.focus_set()
    else:
        G.set_server_state(False)
        server_list_page.pack(fill='both',expand=True)
        for i in G.get_peer_server_list():
            server_list.insert(1, i)
        center_window(root)
        # [LATER] Implement TCP connection to server 
    login_page.pack_forget()

def logout(G):
    server_list.delete(0,tk.END)
    G.logout()
    logout_shout(G)
    loggedin_l.configure(text="Logged in as: ")
    server_page.pack_forget()
    server_list_page.pack_forget()
    login_page.pack(fill='both',expand=True)
    center_window(root)
    uname_t.focus_set()

# [LATER] Will need to revamp with connected peer
def send_message(event,G):
    message_list.configure(state='normal')
    message_list.insert('end',G.get_username()+": "+my_message.get()+'\n')
    message_list.configure(state='disabled')
    my_message.delete(0,'end')

def game_loop(G,area):
    GAME=gameState(area,g_text_e)
    test = ["the","five","boxing","wizards","jump","quickly"]
    for i in test:
        GAME.spawn_word(i)
    while G.get_app_status():
        dbg(g_text_e.get())
        #dbg("Game loop",i)
        GAME.update()
        time.sleep(0.5)

def test_game(G):
    server_page.pack_forget()
    game_page.pack(fill='both',expand=True)
    g_text_e.focus_set()
    #center_window(root)
    threading.Thread(target=game_loop,args=(G,g_canvas)).start()

# tk validation function, to make sure there's no spaces in the "username" field and restrict to 16 characters
def valuser(newchar, current_string):
    if( ' ' not in newchar and len(current_string) <= 15 ):
        return True
    else:
        return False
vcmd = root.register(valuser)

# Create a style, and templates that can be used for elements when using said style
style = ttk.Style()
style.configure("M.TLabel", foreground="black", font=('Ariel',25))
style.configure("M.TLabel", foreground="black", font=('Ariel',15))
style.configure("M.TEntry", foreground="red") # For some reason Entry font can't be declared outside
style.configure("M.TButton", font=('Ariel',25))
style.configure("S.TButton", font=('Ariel',15))

# ----------------------------------------------
#                   VARIABLES
# ----------------------------------------------

# GUI variables
login_page = ttk.Frame(root)
server_page = ttk.Frame(root)
server_list_page = ttk.Frame(root)
game_page = ttk.Frame(root)

# Message app variables
server_cache = {}
username=tk.StringVar()
messages=tk.StringVar()
word_list=[]

with open("words.txt","r") as f:
    for i in f:
        word_list.append(i[:-1].lower())
print(word_list[15121])

# Network variables
udp_listener_thread = threading.Thread(target=udp_peer_listener,args=(GG,))
tcp_listener_thread = threading.Thread(target=tcp_peer_listener,args=(GG,))

try:
    udp_listener_socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mreq = socket.inet_aton(MCAST_GROUP) + socket.inet_aton(MY_IP)
    udp_listener_socket.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    udp_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
    udp_listener_socket.settimeout(0.1)
    udp_listener_socket.bind(('',PEER_LISTEN_PORT))
    
    tcp_listener_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_listener_socket.settimeout(0.1)
    #tcp_listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_listener_socket.bind((MY_IP,SERVER_PORT))
except Exception as e:
    dbg("Error creating listener sockets: ",e,d=1)
    sys.exit(1)

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
bottom_f = ttk.Frame(server_page)
loggedin_l = ttk.Label(server_page, text="Logged in as: ", style="M.TLabel")
message_list = tk.Text(server_page, bg='white')
message_list.configure(state='disabled')
logout_b = ttk.Button(server_page, text="Logout", style="S.TButton", command=lambda: logout(GG))
join_b = ttk.Button(server_page, text="Game", style="S.TButton", command=lambda: test_game(GG)) # temp for testing
message_l = ttk.Label(bottom_f, text="Enter message: ", style="M.TLabel")
my_message = ttk.Entry(bottom_f, font=('Ariel',15))
send_b = ttk.Button(bottom_f, text="Send", style="S.TButton", command=lambda e=None,g=GG: send_message(e,g))

# Binding Enter key to allow sending messages
my_message.bind("<Return>",lambda e,g=GG: send_message(e,g))

bottom_f.pack(side=tk.BOTTOM,fill='x')
loggedin_l.pack(padx=10, pady=10, side=tk.LEFT, anchor='n')
message_list.pack(padx=25, pady=25, side=tk.LEFT, fill='both')
logout_b.pack(pady = 20, padx=20, side=tk.TOP)
join_b.pack(pady = 20, padx=20, side=tk.TOP)

message_l.pack(pady = 20, padx=20, side=tk.LEFT, anchor='e')
send_b.pack(pady = 20, padx=20, side=tk.RIGHT)
my_message.pack(pady = 20, padx=20, side=tk.RIGHT, expand=True, fill='x')


# 3rd Window : Server List. If there are other users online, display list.
list_l = ttk.Label(server_list_page, text="List of users online: ", style="M.TLabel")
server_list = tk.Listbox(server_list_page, bg='white')
join_b = ttk.Button(server_list_page, text="Join", style="S.TButton")
logout_b = ttk.Button(server_list_page, text="Logout", style="S.TButton", command=lambda: logout(GG))

list_l.pack(padx=20, pady=20, side=tk.TOP, anchor='nw')
server_list.pack(padx=10, pady=10, side=tk.TOP, fill='x')
join_b.pack(padx=20, pady=20, side=tk.LEFT, anchor='nw')
logout_b.pack(padx=20, pady=20, side=tk.RIGHT, anchor='nw')

# 4th Test Window : Actual game (testing, iterate)
g_canvas = tk.Canvas(game_page, bg="#000000")
g_text_f = ttk.Frame(game_page)
g_text_f.pack(side=tk.BOTTOM,fill='x')
g_text_l = ttk.Label(g_text_f, text="Destroy the words by typing them! : ", style="M.TLabel")
g_text_e = ttk.Entry(g_text_f, font=('Ariel',15))
g_text_e.insert(0,'sample')

g_text_l.pack(padx=10, pady=20, side=tk.LEFT)
g_text_e.pack(padx=10, pady=20, side=tk.LEFT,fill='x',expand=True)
g_canvas.pack(fill='both',expand=True)

# Main window loop
def main():
    # Start threads
    udp_listener_thread.start()
    tcp_listener_thread.start()
    # Display login page
    login_page.pack(fill='both',expand=True)
    uname_t.focus_set()    
    root.mainloop()

# Script import protection
if __name__ == '__main__':
    main()
