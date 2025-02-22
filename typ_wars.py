import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk
import socket
import threading
from threading import Event
import time
import random
import datetime

# Small section to get screen dimensions
rope = tk.Tk()
rope.update_idletasks()
rope.attributes('-fullscreen', True)
rope.state('iconic')
SCREEN_SIZE = rope.winfo_geometry()
screen_height = rope.winfo_height()
screen_width = rope.winfo_width()
rope.destroy()

# Main window definition, title and dimensions
root = tk.Tk()
root.title("Typ Wars")
root.resizable(False, False)
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
        self.threadz=True
        self.readySignal=tk.BooleanVar()
        #self.readySignal.set(False)
        #self.GAME = gameState() # dynamic

    # Display and send messages you type
    def send_message(self,msg,signal=False):
        if signal:                              # Not a chat message, but a system message
            txt = msg+'\n'
        else:
            txt = self.userName+": "+msg+'\n'
            host_my_message.delete(0,'end')
        display_message(txt)
        if hasattr(self,"connectedPeer"):
            if signal:
                self.send_to_peer("SIG|"+txt)
            else:
                self.send_to_peer("MSG|"+txt)

    def game_send_word(self,word):
        self.send_to_peer("GAME|"+word+"|"+SCORE.get())

    def game_recv_word(self,word):
        part=word.partition("|")
        self.GAME.spawn_word(part[0],part[2])
    
    def you_win(self):
        self.STATE="WIN"
    # Display messages sent by your peer
    def recv_message(self,msg,signal=False):
        if signal:
            txt = msg
        else:
            txt = msg
        display_message(txt)

    # Functions to change game state
    def start_login(self,username):
        with self.gLock:
            self.userName=username
    def login_success(self):
        with self.gLock:
            self.STATE="LOGGED_IN"
    def logout(self):   
        with self.gLock:
            self.username=''
            self.STATE="START"
            self.isServer=False
            if hasattr(self,"connectedPeer"):
                self.peer_disconnect()
    def set_server_state(self,state):
        with self.gLock:
            self.isServer=state
    def add_peer(self,hostname,address):
        with self.gLock:
            self.peerCache[hostname]=address
            if hostname not in self.peerIsServer:
                self.peerIsServer[hostname]=False
    def remove_peer(self,hostname):
        with self.gLock:
            del self.peerCache[hostname]
            del self.peerIsServer[hostname]
    def update_peer_server_status(self,hostname,status):
        with self.gLock:
            self.peerIsServer[hostname]=status
    def start_game(self,area,game_text_entry,words):
        if self.isServer:
            self.send_message("[ Game has started! ]",True)
        else:
            display_message("[ "+self.userName+" is Playing alone.. ]\n")
        with self.gLock:
            self.STATE="IN_GAME"
            self.GAME=gameState(area,game_text_entry,words)
    def exit_game(self,from_peer=False):
        self.GAME.end_game()
        game_page.pack_forget()
        if from_peer:                                                       # Exit from peer in multiplayer
            if self.STATE=="WIN":
                self.STATE="LOGGED_IN"
                display_message("[ Game has ended ]\n")
            else:
                self.STATE="GAME_QUIT_PEER"
                display_message("[ "+self.connectedPeer+" quit the game ]\n")
        elif hasattr(self,"connectedPeer"):                                 # Exit from here in multiplayer
            if self.STATE=="LOSE":
                self.STATE="LOGGED_IN"
                display_message("[ Game has ended ]\n")
            else:
                self.STATE="GAME_QUIT_ME"
                display_message("[ "+self.userName+" quit the game ]\n")
        else:
            self.STATE="GAME_QUIT_ME"
            display_message("[ "+self.userName+" quit the game ]\n")
    def exit_app(self):
        with self.gLock:
            self.threadz=False
    def peer_connect(self,peer,conn):
        GTEST_BUTTON.pack_forget()
        host_peer_label.configure(text="Connected: "+peer)
        host_disconnect_button.pack(pady = 20, padx=20, side=tk.TOP)
        with self.gLock:
            self.connectedPeer=peer
            self.peerSocket=conn
            self.sendWaiter=threading.Event()
            self.sendBuffer=''
            self.peerSocket.settimeout(0.1)
            #self.peerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 5)
            self.disconWaiter = threading.Event()
            self.readySignal.set(False)
            self.rcv_loop = threading.Thread(target=game_receive_loop,args=(self,))
            self.send_loop = threading.Thread(target=game_send_loop,args=(self,))
            self.dcloop = threading.Thread(target=peer_disconnect_handler,args=(self,))
        if not self.isServer:
            host_ready_button.pack(pady = 20, padx=20, side=tk.BOTTOM)
        self.rcv_loop.start()
        self.send_loop.start()
        self.dcloop.start()
        if self.isServer:
            self.send_message("[ "+self.connectedPeer+" has joined ]",True)
    def peer_disconnect(self,from_peer=False):
        self.dc_from_peer=from_peer                         # Do not delete, required by peer_disconnect_handler
        if self.isServer:
            GTEST_BUTTON.pack(pady=20, padx=20, side=tk.TOP)
            if from_peer:
                display_message("[ "+self.connectedPeer+" has left ]\n")
            else:
                display_message("[ "+self.connectedPeer+" has been kicked ]\n")
        else:
            display_message("",True)
        self.disconWaiter.set()
        host_ready_button.pack_forget()
        host_disconnect_button.pack_forget()
        host_start_button.pack_forget()
        host_peer_label.configure(text="No player connected.")
        if not self.isServer and self.STATE!="START":   # Change window for disconnect as client, i.e. not logout or exit
            server_page.pack_forget()
            if from_peer:
                warning_popup(root, "You have been kicked !")
            server_list_page.pack(expand=True,fill='both')
            center_window(root)
    def ready_toggle(self,from_peer=False):
        if from_peer:                               # Only if you are server
            self.readySignal.set(not self.readySignal.get())
            if self.readySignal.get():
                host_start_button.pack(pady = 20, padx=20, side=tk.BOTTOM)
            else:
                host_start_button.pack_forget()
        if not from_peer:
            self.send_to_peer("__READY__")
            while self.sendWaiter.is_set():              # Wait until ready signal is sent
                pass
            if self.readySignal.get():
                self.send_message("[ "+self.userName+" is Ready to Play! ]",True)
            else:
                self.send_message("[ "+self.userName+" is not Ready.. ]",True)
    def send_to_peer(self,msg):                         # Using gLock here will lead to deadlock
        while self.sendWaiter.is_set():                 # Finish any pending send operation before starting another one
            pass
        self.sendBuffer=msg
        self.sendWaiter.set()
    # Functions to read game state
    def get_app_status(self):
        with self.gLock:
            return self.threadz
    def am_i_server(self):
        with self.gLock:
            return self.isServer
    def get_peer_cache(self):
        with self.gLock:
            # Basically, __TEMP__ addresses are created for peers with same hostname to avoid peer_shout loop in udp_host_peer_labelistener, and will usually get
            # deleted immediately after the peer sends logout_shout. This "if", is there to handle any micro issues that may arise due to
            # referencing peerCache while those placeholder addresses are still present in it.
            if "__TEMP__" in self.peerCache.values():
                for h,a in self.peerCache.copy().items():
                    if a=="__TEMP__":
                        del self.peerCache[h]
            return self.peerCache
    def get_peer_cache_UNCLEAN_DO_NOT_USE(self): # My clever "solution" just causes the loop again...
        with self.gLock:
            return self.peerCache # This is a bandaid fix which will likely be permanent, PLEASE do not use this function outside udp_host_peer_labelistener !
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
    def get_connected_peer(self):
        with self.gLock:
            if hasattr(self,"connectedPeer"):
                return self.connectedPeer
            else:
                return None

GG=globalState()

class gameState:
    def __init__(self,area,field,words,button=None):
        self.goodWords = words                      # list of acceptable words
        self.screenWords = {}                       # list of words on screen
        self.h_tick = screen_height/100
        self.spawnArea = screen_width*(2/3)
        self.w_tick = 100
        self.difficulty = 0
        self.speed = [ 0.8, 0.7, 0.6, 0.5, 0.35, 0.2 ]
        self.wordLength = [ 4, 6, 8, 10, 12, 50 ]
        self.screenLimit = [ 3, 3, 4, 4, 5, 5 ]
        self.diffScore = [ 100, 200, 300, 400, 500, 1000 ]
        self.wordCount = 0
        self.screen=area
        self.textField = field
        self.textField.bind( "<Return>", lambda e: self.word_entered(e) )
        self.gameLock = threading.Lock()
        self.sendWord = ''
    def set_peer(self):
        self.peerScore=0
        game_peer_score_label.pack(padx=20, pady=20, side=tk.LEFT)
        game_peer_score.pack(pady=20, side=tk.LEFT)
    def spawn_word(self,word,score=''):
        if score:
            PEER_SCORE.set(score)
        if not word:
            return
        if word in self.screenWords:
            self.word_DELETE(word)
            # Peer helped you out lol!
        else:
            self.word_INSERT(word)
            self.w_tick += (self.spawnArea/6)
            if self.w_tick > self.spawnArea:
                self.w_tick=100
    def end_game(self):
        self.screen.delete("all")
        self.textField.delete(0,'end')
        LIFE.set("3")
        SCORE.set("0")
        game_peer_score_label.pack_forget()
        game_peer_score.pack_forget()
        if hasattr(self,"peerScore"):
            delattr(self,"peerScore")
    def word_INSERT(self,word):
        with self.gameLock:
            t=self.screen.create_text(self.w_tick,50,text=word,fill="#FFFFFF",font=("Arial",20))
            self.screenWords[word]=t
            self.wordCount+=1
    def word_DELETE(self,word):
        with self.gameLock:
            self.screen.delete(self.screenWords[word])
            del self.screenWords[word]
            self.wordCount-=1
    def score_UP(self):
        s=int(SCORE.get())
        s+=5
        SCORE.set( str(s) )
        self.sendWord="__SCORE__"
        return s
    def word_entered(self,event):
        word=self.textField.get()
        self.textField.delete(0,'end')
        if word in self.screenWords:
            self.word_DELETE(word)
            s=self.score_UP()
            if s > self.diffScore[self.difficulty] and self.difficulty < 6:   # Raise difficulty when score reaches certain thresholds
                self.difficulty+=1
        elif word in self.goodWords:
            # SEND WORD TO ENEMY
            self.sendWord = word
            
    def multi_player_update(self):
        if self.wordCount < 2:
            v = random.randrange(len(self.goodWords))
            while (self.goodWords[v] in self.screenWords) or (len(self.goodWords[v]) > self.wordLength[self.difficulty] ):
                v = random.randrange(len(self.goodWords))
            self.spawn_word(self.goodWords[v])
        for i in self.screenWords.copy():
            with self.gameLock:
                self.screen.move(self.screenWords[i],0,self.h_tick)
            if self.screen.coords(self.screenWords[i])[1] > (screen_height*(2/3)-15):
                self.word_DELETE(i)
                # [LATER] DAMAGE FX !
                l=int(LIFE.get())-1
                LIFE.set(str(l))
    def single_player_update(self):
        if self.wordCount < self.screenLimit[self.difficulty]:
            v = random.randrange(len(self.goodWords))
            while (self.goodWords[v] in self.screenWords) or (len(self.goodWords[v]) > self.wordLength[self.difficulty] ):
                v = random.randrange(len(self.goodWords))
            self.spawn_word(self.goodWords[v])
        for i in self.screenWords.copy():
            with self.gameLock:
                self.screen.move(self.screenWords[i],0,self.h_tick)
            if self.screen.coords(self.screenWords[i])[1] > (screen_height*(2/3)-15):
                self.word_DELETE(i)
                # [LATER] DAMAGE FX !
                l=int(LIFE.get())-1
                LIFE.set(str(l))

# ----------------------------------------------
#               NETWORKING CONSTANTS
# ----------------------------------------------

# Function to get local IP
def get_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as ipsock:
        ipsock.connect(("8.8.8.8",1))
        return ipsock.getsockname()[0]
MY_IP = get_ip()
MCAST_GROUP = "224.1.1.251"
MAGIC = "$%1~.!@#typ_wars#@!.~1%$"
PEER_LISTEN_PORT=3001
SERVER_PORT=3002
GAME_PORT=3003
TTL=2

# ----------------------------------------------
#                 GENERAL FUNCTIONS 
# ----------------------------------------------

dbg_file = open("debug.txt","a")

# For debugging
def dbg(*args,d=0):
    if d==0:
        print(*args) # Remove for production
    else:
        # Log exceptions
        current_datetime = datetime.datetime.now()
        formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
        dbg_file.write(formatted_datetime+": ")
        for i in args:
            dbg_file.write(str(i)+" ")
        dbg_file.write('\n')

# Center the window
def center_window(window):
    window.update()
    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    #window.update()
    window.geometry(f"{width}x{height}+{x}+{y}")
    #window.geometry(f"+{x}+{y}")

# Refresh the display of servers on the client page
def server_display_refresh(G):
    join_server_list.delete(0,tk.END)
    j=1
    for i in G.get_peer_server_list():
        join_server_list.insert(j, i)
        j+=1

# Clean up threads etc. and make a graceful exit
def quit_program(G):
    if G.STATE == "IN_GAME":
        G.exit_game()
    logout_shout(G)
    G.logout()
    G.exit_app()
    udp_listener_thread.join()
    tcp_listener_thread.join()
    root.destroy()
    dbg_file.close()

# Force use above function when main window is closed in any form
root.protocol('WM_DELETE_WINDOW', lambda: quit_program(GG))

def warning_popup(window, warning_text):
    window.wm_attributes('-type', 'splash')
    tk.messagebox.showwarning(title="Warning!", message=warning_text)
    window.wm_attributes('-type', 'normal')

# ----------------------------------------------
#           CLIENT NETWORKING FUNCTIONS 
# ----------------------------------------------

# ===!        UDP Shout Functions          !=== #

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

# ===!        TCP Ping Functions          !=== #

# Inform a peer that I am a server now
def server_inform(addr):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test:
        try:
            test.connect((addr,SERVER_PORT))
        except Exception as e:
            return
        test.sendall((MAGIC+"IM_SERVER").encode())

# Check if a peer is a server
def server_ping(addr):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test:
        try:
            test.connect((addr,SERVER_PORT))
        except Exception as e:
            dbg("Unable to ping server: ",addr," due to : ",e,d=1)
            return False
        m=MAGIC+"IS_SERVER"
        test.sendall(m.encode())
        reply=test.recv(1024).decode()
        if reply[len(MAGIC):]=="YES" and reply.startswith(MAGIC):
            return True
        else:
            return False

# Refresh list of servers
def server_refresh(G):
    servers=G.get_peer_cache().copy()
    for host,addr in servers.items():
        G.update_peer_server_status(host,server_ping(addr))

# Join a server as a client
def join_host(event,G,widget):
    host=widget.get(widget.curselection()[0])
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test:
        try:
            test.connect((G.get_peer_cache()[host],SERVER_PORT))
        except Exception as e:
            dbg("Can't join ",host," on Server port due to: ",e,d=1)
            return
        m=MAGIC+"CONNECT"
        test.sendall(m.encode())
        reply=test.recv(1024).decode()
        if reply.startswith(MAGIC) and reply[len(MAGIC):].startswith("YES"):
            r = reply[len(MAGIC+"YES"):-1]                                      # Chat log of host
            display_message(r)
            try:
                ggame = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                
                ggame.connect((G.get_peer_cache()[host],GAME_PORT))
            except Exception as e:
                dbg("Can't join ",host," on Game port: ",e,d=1)
                return
            G.peer_connect(host,ggame)
            server_list_page.pack_forget()
            server_page.pack(expand=True,fill='both')
            center_window(root)
            host_my_message.focus_set()
        else:
            dbg("ERROR! ",host,"is not a server!",d=1)
            return
        #"""

# ----------------------------------------------
#           SERVER NETWORKING FUNCTIONS 
# ----------------------------------------------

# ===!        Listener Functions          !=== #

# Running as thread from start
def udp_peer_listener(G):
    while G.get_app_status():
        try:
            data, addr = udp_listener_socket.recvfrom(1024)
        except TimeoutError:
            continue
        except Exception as e:
            dbg("Closing UDP Listener due to Error: ",e,d=1)
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
            if G.get_state()=="START":                              # If I haven't logged in, add the address
                G.add_peer(rec_user,addr[0])
            else:
                if rec_user == G.get_username():                    # Placeholder for duplicate username, will usually be deleted immediately.
                    G.add_peer(rec_user,"__TEMP__")                 # Avoids peer_shout loop.
                else:
                    G.add_peer(rec_user,addr[0])
                # <-- SEND (PEER SHOUT)
                peer_shout(G)
                

            # ~ if G.get_state()=="LOGGED_IN":
                # ~ if rec_user != G.get_username():
                    # ~ G.add_peer(rec_user,addr[0])
                # ~ else:
                    # ~ G.add_peer(rec_user,"__TEMP__") # Placeholder for duplicate username, will usually be deleted immediately. Avoids peer_shout loop.
                # ~ # <-- SEND (PEER SHOUT)
                # ~ peer_shout(G)
            # ~ # I'm not logged in yet
            # ~ else:
                # ~ G.add_peer(rec_user,addr[0]) # server_ping(addr[0]))

# Running as thread from the start
def tcp_peer_listener(G):
    tcp_listener_socket.listen(5)
    while G.get_app_status():
        try:
            new_con, new_addr = tcp_listener_socket.accept()
            threading.Thread(target=server_process,args=(G,new_con,new_addr)).start()
        except TimeoutError:
            continue
        except Exception as e:
            dbg("Closing TCP Listener due to Error: ",e,d=1)
            tcp_listener_socket.close()
            break

# Split from "tcp_peer_listener" thread
def server_process(G,conn,addr):
    m = conn.recv(1024).decode()
    host=list(G.get_peer_cache().keys())[list(G.get_peer_cache().values()).index(addr[0])]
    if m.startswith(MAGIC):
        msg=m[len(MAGIC):]
    else:
        return
    if msg=="IS_SERVER":                            # From server_ping
        if G.am_i_server():
            conn.sendall((MAGIC+"YES").encode())
        else:
            conn.sendall((MAGIC+"NO").encode())
    elif msg=="IM_SERVER":                          # From server_inform
        G.update_peer_server_status(host,True)
        server_display_refresh(G)
    elif msg=="CONNECT":                            # From join_host
        if G.am_i_server():
            conn.sendall((MAGIC+"YES"+host_chat_display.get("1.0",tk.END)).encode())
            # Set up TCP threads for sending and receiving (as server) here
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as glisten:
                glisten.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                glisten.bind((MY_IP,GAME_PORT))
                glisten.listen(1)
                try:
                    ggame, new_addr = glisten.accept()
                except Exception as e:
                    dbg("ERROR! Could not connect to game due to: ",e,d=1)
                    return
                G.peer_connect(host,ggame)
        else:
            conn.sendall((MAGIC+"NO").decode())

# ----------------------------------------------
#         CHAT & GAME NETWORK FUNCTIONS 
# ----------------------------------------------

def game_receive_loop(G):
    while hasattr(G,"connectedPeer"):
        try:
            m = G.peerSocket.recv(1024).decode()
        except TimeoutError:
            continue
        except Exception as e:
            dbg("ERROR! Closing game receive loop due to: ",e,d=1)
            G.peer_disconnect()
            return
        # Process message
        if m.startswith(MAGIC):
            msg=m[len(MAGIC):]
        else:
            continue
        if msg.startswith("MSG|"):
            G.recv_message(msg[4:])
        elif msg.startswith("SIG|"):
            G.recv_message(msg[4:],True)
        elif msg.startswith("GAME|"):
            G.game_recv_word(msg[5:])
        elif msg.startswith("__START__"):
            ready_game(G,True)
        elif msg.startswith("__READY__"):
            G.ready_toggle(True)
        elif msg.startswith("__EXIT__"):
            G.exit_game(True)
        elif msg.startswith("__GAMEOVER__"):
            G.you_win()
        elif msg=="__DISCONNECT__":
            G.peer_disconnect(True)
            return

def game_send_loop(G):
    while hasattr(G,"sendWaiter"):
        G.sendWaiter.wait()
        if not hasattr(G,"connectedPeer"):
            break
        msg=G.sendBuffer
        G.sendBuffer=''
        G.sendWaiter.clear()
        m = MAGIC+msg
        try:
            G.peerSocket.sendall(m.encode())
        except Exception as e:
            dbg("ERROR! Closing game send loop due to: ",e,d=1)
            G.peer_disconnect(True)
            return
        if msg=="__DISCONNECT__":
            return
    
def peer_disconnect_handler(self):
    self.disconWaiter.wait()                        # Flag to set for when you want to disconnected, will wait here
    with self.gLock:
        if self.dc_from_peer:                       # If disconnect message came from peer
            self.rcv_loop.join()
            delattr(self,"connectedPeer")
            self.sendWaiter.set()
            self.send_loop.join()
        else:                                       # If you are the one sending the disconnect message
            self.send_to_peer("__DISCONNECT__")
            self.send_loop.join()
            delattr(self,"connectedPeer")
            self.rcv_loop.join()
        delattr(self,"dc_from_peer")
        self.peerSocket.close()
        delattr(self,"peerSocket")
        delattr(self,"sendWaiter")
        delattr(self,"sendBuffer")
        delattr(self,"rcv_loop")
        delattr(self,"send_loop")
        delattr(self,"disconWaiter")

# ----------------------------------------------
#               GAME FUNCTIONS 
# ----------------------------------------------

def singleplayer_game_loop(G,area):
    G.start_game(area,game_text_entry,word_list)
    while G.STATE=="IN_GAME":
        G.GAME.single_player_update()
        if int(LIFE.get()) == 0:
            warning_popup(root,"Game over!\nFinal Score: "+SCORE.get())
            G.exit_game()
            break
        time.sleep(G.GAME.speed[G.GAME.difficulty])
    if G.STATE=="GAME_QUIT_ME":
        warning_popup(root,"Game ended!")
    host_disconnect_button.pack(pady = 20, padx=20, side=tk.BOTTOM)
    server_page.pack(expand=True,fill='both')
    center_window(root)
    host_disconnect_button.pack_forget()
    host_my_message.focus_set()
    delattr(G,"GAME")

def multiplayer_game_loop(G,area):
    G.start_game(area,game_text_entry,word_list)
    G.GAME.set_peer()
    while G.STATE=="IN_GAME":
        G.GAME.multi_player_update()
        if int(LIFE.get()) == 0:
            G.send_to_peer("__GAMEOVER__")
            G.STATE="LOSE"
            warning_popup(root,"You LOSE !\nOpponent: "+PEER_SCORE.get()+"\nYou: "+SCORE.get())
            G.exit_game()
            break
        elif G.GAME.sendWord:
            if G.GAME.sendWord=="__SCORE__":
                G.game_send_word('')
            else:
                G.game_send_word(G.GAME.sendWord)
            G.GAME.sendWord=''
        time.sleep(G.GAME.speed[G.GAME.difficulty])
    if G.STATE=="WIN":
        warning_popup(root,"You WIN !\nOpponent: "+PEER_SCORE.get()+"\nYou: "+SCORE.get())
        G.exit_game()
    elif G.STATE=="GAME_QUIT_ME":
        G.STATE="LOGGED_IN"
        G.send_to_peer("__EXIT__")
    elif G.STATE=="GAME_QUIT_PEER":
        warning_popup(root, G.connectedPeer+" quit!")
    server_page.pack(expand=True,fill='both')
    center_window(root)
    host_my_message.focus_set()
    delattr(G,"GAME")

def ready_game(G,from_peer=False):
    if not from_peer and hasattr(G,"connectedPeer"):
        G.send_to_peer("__START__")
    server_page.pack_forget()
    game_page.pack(fill='both',expand=True)
    center_window(root)
    # [LATER] Some form of countdown?
    game_text_entry.focus_set()
    if hasattr(G,"connectedPeer"):
        threading.Thread(target=multiplayer_game_loop,args=(G,game_canvas)).start()
    else:
        threading.Thread(target=singleplayer_game_loop,args=(G,game_canvas)).start()

# ----------------------------------------------
#               TKINTER FUNCTIONS 
# ----------------------------------------------

# Login function
def login(event,G):
    if not login_uname_entry.get():
        warning_popup(root,"No username entered")
        return
    elif login_uname_entry.get()=="#@!__EXIT__!@#":
        warning_popup(root,"Don't be sneaky now ~ ^_^")
        return
    elif login_uname_entry.get() in G.get_peer_cache():
        warning_popup(root,"User already exists!")
        return
    
    G.start_login(login_uname_entry.get()) # Set game state for login
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
    
    # Check whether your username is already taken
    if login_uname_entry.get() in G.get_peer_cache():
        logout(G)
        warning_popup(root,"User already exists!")
        return
    
    # Check peers to update which are in Server mode right now
    server_refresh(G)
    
    G.login_success()
    host_loggedin_label.configure(text=host_loggedin_label.cget("text")+G.get_username())
    if not G.get_peer_server_list():
		# If there's no other server online, set this system to be server
        G.set_server_state(True)
        for addr in G.get_peer_cache().values():
            server_inform(addr)
        host_disconnect_button.pack(pady = 20, padx=20, side=tk.TOP)
        server_page.pack(expand=True,fill='both')
        center_window(root)
        host_disconnect_button.pack_forget()
        host_my_message.focus_set()
    else:
        G.set_server_state(False)
        for i in G.get_peer_server_list():
            join_server_list.insert(1, i)
        server_list_page.pack(fill='both',expand=True)
        center_window(root)
        # [LATER] Implement TCP connection to server 
    login_page.pack_forget()

def logout(G):
    join_server_list.delete(0,tk.END)
    G.logout()
    logout_shout(G)
    host_loggedin_label.configure(text="Logged in as: ")
    display_message("",True)
    server_page.pack_forget()
    server_list_page.pack_forget()
    login_page.pack(fill='both',expand=True)
    center_window(root)
    login_uname_entry.focus_set()

# Display message coming from state machine handler on the chat display window
def display_message(text,clear=False):
    host_chat_display.configure(state='normal')
    if clear:
        host_chat_display.delete('1.0', tk.END)
    else:
        host_chat_display.insert('end',text)
    host_chat_display.configure(state='disabled')

# tk validation function, to make sure there's no spaces in the "username" field and restrict to 16 characters
def valuser(newchar, current_string):
    if( ' ' not in newchar and len(current_string) <= 15 ):
        return True
    else:
        return False
vcmd = root.register(valuser)

# Proxy function to send message from TKInter to State machine's message handler
def msg_proxy(event,G,widget):
    t=widget.get()
    G.send_message(t)

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

# Tkinter Styles
# Create a style, and templates that can be used for elements when using said style
style = ttk.Style()
style.configure("M.TLabel", foreground="black", font=('Ariel',25))
style.configure("M.TLabel", foreground="black", font=('Ariel',15))
style.configure("M.TEntry", foreground="red") # For some reason Entry font can't be declared outside
style.configure("M.TButton", font=('Ariel',25))
style.configure("S.TButton", font=('Ariel',15))
style.configure("S.TCheckbutton", font=('Ariel',15))#, indicatorbackground="white", indicatorforeground="green")
img_unticked_box = tk.PhotoImage(file="assets/0.png")
img_ticked_box = tk.PhotoImage(file="assets/1.png")
style.element_create("tickbox", "image", img_unticked_box, ("selected", img_ticked_box))
# Replace the checkbutton indicator with the custom tickbox in the Checkbutton's layout
style.layout(
    "TCheckbutton", 
    [('Checkbutton.padding',
      {'sticky': 'nswe',
       'children': [('Checkbutton.tickbox', {'side': 'left', 'sticky':     ''}),
    ('Checkbutton.focus',
         {'side': 'left',
          'sticky': 'w',
      'children': [('Checkbutton.label', {'sticky': 'nswe'})]})]})]
)

# Word file
with open("words.txt","r") as f:
    for i in f:
        word_list.append(i[:-1].lower())

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
    tcp_listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #tcp_listener_socket.shutdown(socket.SHUT_RDWR)
    #tcp_listener_socket.close()
    tcp_listener_socket.bind((MY_IP,SERVER_PORT))
except Exception as e:
    dbg("FATAL ERROR! Cannot create listener sockets because: ",e,d=1)
    sys.exit(1)

# ! LOGIN SCREEN !
# Enter username label and textbox (all rooted to login_page frame)
login_uname_label = ttk.Label(login_page, text="Enter username", style="M.TLabel")
login_uname_entry = ttk.Entry(login_page, style="M.TEntry", font=('Ariel',25), validate='key', validatecommand=(vcmd,"%S","%P")) # %S : Newly entered char, %P : Current full text
login_enter_button = ttk.Button(login_page, text="Enter", style="M.TButton", command=lambda e=None,g=GG: login(e,g)) # I AM A GENIUS! ...ahem, well that was a nice fix
login_quit_button = ttk.Button(login_page, text="Quit", style="M.TButton", command=lambda: quit_program(GG))

# Binding Enter key to allow login
login_uname_entry.bind("<Return>",lambda e,g=GG: login(e,g))

# Pack everything so that they display on screen
login_uname_label.pack(pady = 10)
login_uname_entry.pack(padx = 20, pady = 10)
login_enter_button.pack(pady = 20, padx=20, side=tk.LEFT)
login_quit_button.pack(pady = 20, padx = 20, side=tk.RIGHT)

# ! SERVER HOST SCREEN !
# If there are no other users online, you will become the host for the chatroom.
host_bottom_frame = ttk.Frame(server_page)
host_loggedin_label = ttk.Label(server_page, text="Logged in as: ", style="M.TLabel")
host_peer_label = ttk.Label(server_page, text="No player connected.", style="M.TLabel")
host_chat_display = tk.Text(server_page, bg='white', height=1)
host_chat_display.configure(state='disabled')
host_logout_button = ttk.Button(server_page, text="LOGOUT", style="S.TButton", command=lambda: logout(GG))

host_disconnect_button = ttk.Button(server_page, text="DISCONNECT", style="S.TButton", command=GG.peer_disconnect)
host_ready_button = ttk.Checkbutton(server_page, text="READY", style="S.TCheckbutton", command=GG.ready_toggle, variable=GG.readySignal)
host_start_button = ttk.Button(server_page, text="START", style="S.TButton", command=lambda: ready_game(GG))
GTEST_BUTTON = ttk.Button(server_page, text="SOLO PLAY", style="S.TButton", command=lambda: ready_game(GG)) # Play Singleplayer

host_message_label = ttk.Label(host_bottom_frame, text="Enter message: ", style="M.TLabel")
host_my_message = ttk.Entry(host_bottom_frame, font=('Ariel',15))
host_send_button = ttk.Button(host_bottom_frame, text="Send", style="S.TButton", command=lambda e=None,G=GG,widget=host_my_message : msg_proxy(e,G,widget))

# Binding Enter key to allow sending messages
host_my_message.bind("<Return>", lambda e="<Return>",G=GG,widget=host_my_message : msg_proxy(e,G,widget))

host_bottom_frame.pack(side=tk.BOTTOM,fill='x')
host_loggedin_label.pack(padx=10, pady=10, side=tk.TOP)
host_peer_label.pack(padx=10, pady=10, side=tk.TOP)
host_chat_display.pack(padx=25, pady=25, side=tk.LEFT, expand=True, fill='both')
host_logout_button.pack(pady = 20, padx=20, side=tk.TOP)
#host_disconnect_button.pack(pady = 20, padx=20, side=tk.TOP)

#host_ready_button.pack(pady = 20, padx=20, side=tk.TOP)
#host_start_button.pack(pady = 20, padx=20, side=tk.TOP)
GTEST_BUTTON.pack(pady=20, padx=20, side=tk.TOP)

host_message_label.pack(pady=20, padx=20, side=tk.LEFT, anchor='e')
host_send_button.pack(pady=20, padx=20, side=tk.RIGHT)
host_my_message.pack(pady=20, padx=20, side=tk.RIGHT, expand=True, fill='x')

# ! SERVER LIST SCREEN !
# If there are other users online, display list.
join_list_label = ttk.Label(server_list_page, text="List of users online: ", style="M.TLabel")
join_server_list = tk.Listbox(server_list_page, bg='white',selectmode="single")
join_join_button = ttk.Button(server_list_page, text="Join", style="S.TButton")
join_logout_button = ttk.Button(server_list_page, text="Logout", style="S.TButton", command=lambda: logout(GG))
join_join_button.configure(command=lambda e=None,g=GG,s=join_server_list: join_host(e,g,s))
join_server_list.bind("<Double-Button-1>", lambda e,g=GG,s=join_server_list: join_host(e,g,s))

join_list_label.pack(padx=20, pady=20, side=tk.TOP, anchor='nw')
join_server_list.pack(padx=10, pady=10, side=tk.TOP, fill='x')
join_join_button.pack(padx=20, pady=20, side=tk.LEFT, anchor='nw')
join_logout_button.pack(padx=20, pady=20, side=tk.RIGHT, anchor='nw')

# ! GAME SCREEN !
# 4th Test Window : Actual game (testing, iterate)
SCORE=tk.StringVar()
SCORE.set("0")
PEER_SCORE=tk.StringVar()
PEER_SCORE.set("0")
LIFE=tk.StringVar()
LIFE.set("3")
game_top_frame = ttk.Frame(game_page)
game_top_frame.pack(side=tk.TOP,fill='x')
game_lives_label = ttk.Label(game_top_frame, text="Lives: ", style="M.TLabel")
game_life = ttk.Label(game_top_frame, font=('Ariel',15), textvariable=LIFE)
game_score_label = ttk.Label(game_top_frame, text="Score: ", style="M.TLabel")
game_score = ttk.Label(game_top_frame, font=('Ariel',15), textvariable=SCORE)
game_peer_score_label = ttk.Label(game_top_frame, text="Opp. Score: ", style="M.TLabel")
game_peer_score = ttk.Label(game_top_frame, font=('Ariel',15), textvariable=PEER_SCORE)
game_quit_button = ttk.Button(game_top_frame, text="Quit", style="S.TButton", command=GG.exit_game)

game_canvas = tk.Canvas(game_page, bg="#000000")
game_canvas.config(width=screen_width*2/3, height=screen_height*2/3)

game_text_frame = ttk.Frame(game_page)
game_text_frame.pack(side=tk.BOTTOM,fill='x')
game_text_label = ttk.Label(game_text_frame, text="Destroy the words by typing them! : ", style="M.TLabel")
game_text_entry = ttk.Entry(game_text_frame, font=('Ariel',15))

game_lives_label.pack(padx=10, pady=20, side=tk.LEFT)
game_life.pack(padx=10, pady=20, side=tk.LEFT)
game_score_label.pack(padx=10, pady=20, side=tk.LEFT)
game_score.pack(padx=10, pady=20, side=tk.LEFT)
#game_peer_score_label.pack(padx=20, pady=20, side=tk.LEFT)
#game_peer_score.pack(pady=20, side=tk.LEFT)
game_quit_button.pack(padx=10, pady=20, side=tk.RIGHT)
game_text_label.pack(padx=10, pady=20, side=tk.LEFT)
game_text_entry.pack(padx=10, pady=20, side=tk.LEFT,fill='x',expand=True)
game_canvas.pack(fill='both',expand=True)

# ----------------------------------------------
#                   MAIN LOOP
# ----------------------------------------------

# Main window loop
def main():
    # Start threads
    udp_listener_thread.start()
    tcp_listener_thread.start()
    # Display login page
    login_page.pack(fill='both',expand=True)
    center_window(root)
    login_uname_entry.focus_set()
    root.mainloop()

# Script import protection
if __name__ == '__main__':
    main()
