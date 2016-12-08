#!/usr/bin/env python
from utils import make_logger
from threading import Timer
from gameui import GameUI
import Tkinter as tk
from clientconnector import ClientConnector

Log = make_logger()

#TODO: Don't allow ":" in names

class ClientApplication(tk.Frame):
    def __init__(self,master=None,host='localhost'):
        tk.Frame.__init__(self,master)
        self.pikahost = host
        self.servers = []
        self.username = ""
        self.game_frame = None

        self.create_widgets()
        self.show_server_selection()

        self.connector = ClientConnector(host,self)
        self.connector.setDaemon(True)
        self.connector.start()


    def create_widgets(self):
        # ---------- Client tab widgets ----------
        self.create_server_selection()
        self.create_lobby()
        self.pack(fill=tk.BOTH,expand=1)

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

    def show_server_selection(self):
        self.server_selection_frame.pack(fill=tk.BOTH,expand=1)
        self.server_button.pack(fill=tk.X)
        self.username_label.pack()
        self.username_entry.pack(fill=tk.X)
        self.server_box_label.pack()
        self.server_box.pack(fill=tk.BOTH,expand=1)

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
        self.lobby_roomlist = tk.Listbox(self.gamesframe)

    def show_lobby(self):
        self.connector.request_playerlist()
        self.connector.request_roomlist()
        self.lobbyframe.pack(fill=tk.BOTH,side=tk.LEFT,expand=1)
        self.lobby_listframe.pack(fill=tk.Y,side=tk.LEFT)
        self.gamesframe.pack(fill=tk.BOTH,expand=1,side=tk.LEFT, anchor=tk.N)
        self.game_buttonframe.pack(fill=tk.X)
        self.lobby_joinbutton.pack(fill=tk.X, side=tk.LEFT,expand=1)
        self.lobby_hostbutton.pack(fill=tk.X, side=tk.LEFT,expand=1)
        self.game_name_label.pack(fill=tk.X,side=tk.LEFT,expand=1)
        self.game_name_entry.pack(fill=tk.X,side=tk.LEFT,expand=1)
        self.lobby_roomlist.pack(fill=tk.BOTH,expand=1)

    def make_client_list(self,master):
        self.lobby_buttonarea = tk.Frame(master)
        self.lobby_backbutton = tk.Button(self.lobby_buttonarea,text='Leave server',command=self.lobby_back,bg='tomato')
        self.client_list_label = tk.Label(self.lobby_buttonarea,text='Lobby:',pady=5)
        self.client_list = tk.Listbox(master)
        self.lobby_buttonarea.pack(fill=tk.X)
        self.lobby_backbutton.pack(side=tk.LEFT,anchor=tk.NW)
        self.client_list_label.pack(side=tk.LEFT,fill=tk.X)
        self.client_list.pack(fill=tk.Y,expand=1,anchor=tk.NW)

    def lobby_back(self):
        self.client_list.delete(0,tk.END)
        self.connector.leave_server()
        self.hide_lobby()
        self.show_server_selection()

    def hide_lobby(self):
        self.lobbyframe.pack_forget()

    def hide_server_selection(self):
        self.server_selection_frame.pack_forget()

    def draw_game(self):
        self.game_frame = GameUI(self,self.connector)
        self.game_frame.show()

    def abandon_game(self):
        self.destroy_game()
        self.show_lobby()

    def join_game(self):
        print "Dummy!"

    def host_game(self):
        name = self.game_name_entry.get()
        if name:
            self.connector.request_room(name)

    def flash_name(self):
        self.username_entry.configure(bg='orange')
        Timer(0.4,self.clear_flash).start()

    def clear_flash(self):
        self.username_entry.configure(bg='white')

    def update_server_box(self,serv_name,add):
        self.update_listbox(self.server_box,serv_name,add)
        if self.server_box.size() == 1:
            self.server_box.select_set(0)

    def update_client_box(self,client_name,add):
        self.update_listbox(self.client_list,client_name,add)

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

    def mark_red(self,listbox,name,marking):
        try:
            sisu = listbox.get(0,tk.END)
            ind = listbox.get(0,tk.END).index(name)
            colour = 'thistle' if marking else 'white'
            listbox.itemconfig(ind,bg=colour)
        except Exception as e:
            Log.debug("Couldn't mark/unmark %r as red.", name)
            return

    def pick_server(self):
        selected = self.server_box.curselection()
        uname = self.username_entry.get()
        if selected and uname:
            serv_name = selected[0]
            self.connector.join_server(self.server_box.get(serv_name),uname)
        self.flash_name()

    def disconnect(self):
        self.connector.disconnect()

    def destroy_game(self):
        if self.game_frame:
            self.game_frame.destroy()
        self.game_frame = None

app = ClientApplication()
app.master.title("Battleship 2016")
app.mainloop()
app.disconnect()
