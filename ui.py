#!/usr/bin/env python

from utils import make_logger
from threading import Timer
from gameui import GameUI
import mtTkinter.mtTkinter as tk
from clientconnector import ClientConnector
import tkMessageBox
import sys

Log = make_logger()

#TODO: Don't allow ":" in names

"""
The server selection/lobby of the client
"""
class ClientApplication(tk.Frame):
    """
    @param host - the rabbitmq server
    """
    def __init__(self,host='localhost'):
        tk.Frame.__init__(self,None)
        self.pikahost = host
        self.servers = []
        self.username = ""
        self.game_frame = None

        self.create_widgets()

        self.connector = ClientConnector(host,self)
        self.connector.setDaemon(True)
        self.connector.start()

        self.show_server_selection()

    """
    Initializing widgets
    """
    def create_widgets(self):
        # ---------- Client tab widgets ----------
        self.create_server_selection()
        self.create_lobby()
        self.pack_server_selection()
        self.hide_server_selection()
        self.pack_lobby()
        self.hide_lobby()
        self.pack(fill=tk.BOTH,expand=1)

    """
    Initializing the widgets of the server selection window
    """
    def create_server_selection(self):
        self.server_selection_frame = tk.Frame(self)
        self.username_label = tk.Label(self.server_selection_frame,text='Username')
        self.username_entry = tk.Entry(self.server_selection_frame)
        self.server_box_label = tk.Label(self.server_selection_frame,text="Available servers:")
        self.server_box = tk.Listbox(self.server_selection_frame)
        self.server_button = tk.Button(self.server_selection_frame,
                                        text="Connect",
                                        command=self.pick_server,
                                        bg='SeaGreen2')

    """
    Packing the server selection window
    """
    def pack_server_selection(self):
        self.server_selection_frame.pack(fill=tk.BOTH,expand=1)
        self.server_button.pack(fill=tk.X)
        self.username_label.pack()
        self.username_entry.pack(fill=tk.X)
        self.server_box_label.pack()
        self.server_box.pack(fill=tk.BOTH,expand=1)

    """
    Making the server selection window visible and populating it with servers.
    """
    def show_server_selection(self):
        self.pack_server_selection()
        self.connector.ping_servers()

    """
    Initializing the lobby widgets
    """
    def create_lobby(self):
        self.lobbyframe = tk.Frame(self)
        self.lobby_listframe = tk.Frame(self.lobbyframe)
        self.make_client_list(self.lobby_listframe)
        self.gamesframe = tk.Frame(self.lobbyframe)
        self.game_buttonframe = tk.Frame(self.gamesframe)
        self.lobby_joinbutton = tk.Button(self.game_buttonframe,text="Join Game",command=self.join_game)
        self.lobby_hostbutton = tk.Button(self.game_buttonframe,text="Create Game",command=self.host_game)
        self.game_name_label = tk.Label(self.game_buttonframe,text='Game name:')
        self.game_name_entry = tk.Entry(self.game_buttonframe)
        self.game_size_label = tk.Label(self.game_buttonframe,text='Game size:')
        self.game_size_entry = tk.Entry(self.game_buttonframe)
        self.game_size_entry.insert(0, '10')
        self.lobby_roomlist = tk.Listbox(self.gamesframe)

    """
    Packing the lobby widgets
    """
    def pack_lobby(self):
        self.lobby_roomlist.delete(0,tk.END)
        self.lobbyframe.pack(fill=tk.BOTH,side=tk.LEFT,expand=1)
        self.lobby_listframe.pack(fill=tk.Y,side=tk.LEFT)
        self.gamesframe.pack(fill=tk.BOTH,expand=1,side=tk.LEFT, anchor=tk.N)
        self.game_buttonframe.pack(fill=tk.X)
        self.lobby_joinbutton.pack(fill=tk.X, side=tk.LEFT,expand=1)
        self.lobby_hostbutton.pack(fill=tk.X, side=tk.LEFT,expand=1)
        self.game_name_label.pack(fill=tk.X,side=tk.LEFT,expand=1)
        self.game_name_entry.pack(fill=tk.X,side=tk.LEFT,expand=1)
        self.game_size_label.pack(fill=tk.X,side=tk.LEFT,expand=1)
        self.game_size_entry.pack(fill=tk.X,side=tk.LEFT,expand=1)
        self.lobby_roomlist.pack(fill=tk.BOTH,expand=1)

    """
    Making the lobby visible and populating the room- and playerlist.
    """
    def show_lobby(self):
        self.pack_lobby()
        self.connector.request_playerlist()
        self.connector.request_roomlist()

    """
    Initializing the client list (left) side of the lobby
    """
    def make_client_list(self,master):
        self.lobby_buttonarea = tk.Frame(master)
        self.lobby_backbutton = tk.Button(self.lobby_buttonarea,text='Leave server',command=self.lobby_back,bg='tomato')
        self.client_list_label = tk.Label(self.lobby_buttonarea,text='Lobby:',pady=5)
        self.client_list = tk.Listbox(master)
        self.lobby_buttonarea.pack(fill=tk.X)
        self.lobby_backbutton.pack(side=tk.LEFT,anchor=tk.NW)
        self.client_list_label.pack(side=tk.LEFT,fill=tk.X)
        self.client_list.pack(fill=tk.Y,expand=1,anchor=tk.NW)

    """
    The actions that occurs when the back button is pressed in the lobby
    """
    def lobby_back(self):
        self.client_list.delete(0,tk.END)
        self.hide_lobby()
        self.show_server_selection()
        self.connector.leave_server()

    """
    Unpacking the lobby
    """
    def hide_lobby(self):
        self.lobbyframe.pack_forget()

    """
    Unpacking the server selection
    """
    def hide_server_selection(self):
        self.server_selection_frame.pack_forget()

    """
    Initializing the UI of the game
    """
    def draw_game(self):
        self.game_frame = GameUI(self,self.connector)
        self.game_frame.show()

    """
    Destroying the UI of the game.
    """
    def abandon_game(self):
        self.destroy_game()
        self.show_lobby()

    """
    The action called when the player attempts to join a game
    """
    def join_game(self):
        try:
            selection = self.lobby_roomlist.curselection()[0]
            self.connector.join_room(self.lobby_roomlist.get(selection))
        except IndexError:
            return

    """
    The action called when the player attempts to host a game
    """
    def host_game(self):
        name = self.game_name_entry.get()
        size = self.game_size_entry.get()
        try:
            if name and size and "/" not in name and int(size): #TODO kontrolli, et numbriline
                self.connector.request_room(name, size)
        except:
            return

    """
    Flashes the name box orange, though now we also display errors.
    """
    def flash_name(self):
        self.username_entry.configure(bg='orange')
        Timer(0.4,self.clear_flash).start()

    """
    Removing the above flash
    """
    def clear_flash(self):
        self.username_entry.configure(bg='white')

    """
    adding/removing entries from the server box
    @param serv_name - the server name to be added
    @param add - whether we add or remove
    """
    def update_server_box(self,serv_name,add):
        self.update_listbox(self.server_box,serv_name,add)
        if add and self.server_box.size() == 1:
            self.server_box.select_set(0)

    """
    adding/removing entries from the client box
    @param client_name - the name of the client to add
    @param add - whether we add or remove
    """
    def update_client_box(self,client_name,add):
        self.update_listbox(self.client_list,client_name,add)

    """
    adding/removing entries from any listbox
    @param listbox - the listbox which we modify
    @param name - the entry to add/remove
    @param add - whether we add or remove
    """
    def update_listbox(self,listbox,name,add):
        if add:
            if name not in listbox.get(0,tk.END):
                listbox.insert(tk.END,name)
        else:
            try:
                ind = listbox.get(0,tk.END).index(name)
                listbox.delete(ind)
            except Exception as e:
                return

    """
    The function for marking the background of a listbox entry red or white
    @param listbox - the listbox to edit
    @param name - the entry to change
    @param marking - colour red if true, white if false
    """
    def mark_red(self,listbox,name,marking):
        try:
            sisu = listbox.get(0,tk.END)
            ind = listbox.get(0,tk.END).index(name)
            colour = 'thistle' if marking else 'white'
            listbox.itemconfig(ind,bg=colour)
        except Exception as e:
            Log.debug("Couldn't mark/unmark %r as red.", name)
            return

    """
    The action which is called when the user selects a server to join
    """
    def pick_server(self):
        selected = self.server_box.curselection()
        uname = self.username_entry.get()
        if selected and uname and "/" not in uname:
            serv_name = selected[0]
            self.connector.join_server(self.server_box.get(serv_name),uname)
        self.flash_name()

    """
    A disconnect wrapper
    """
    def disconnect(self):
        self.connector.disconnect()

    """
    Destroying the game ui's if need be.
    """
    def destroy_game(self):
        if self.game_frame:
            self.game_frame.destroy()
        self.game_frame = None

    """
    Popups when the username was no good
    @param servername - the server that we tried to connect to
    @param username - the user name which we werent allowed to take
    """
    def notify_rejection(self,servername,username):
        tkMessageBox.showerror("Invalid name!","Server "+servername+" has rejected the name "+username+".")

    """
    Pop-up for when we try to join a closed room where we are not in the game
    @param room - the roomname which we tried to join.
    """
    def notify_closed(self,room):
        tkMessageBox.showerror("Can't join game!","Room "+room+" is currently in a running game which does not contain you.")

"""
really really simple initialization
"""
host = "localhost"
if len(sys.argv) > 1:
    host = sys.argv[1]
app = ClientApplication(host)
app.master.title("Battleship 2016")
app.mainloop()
app.disconnect()
