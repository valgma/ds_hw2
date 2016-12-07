#!/usr/bin/env python
from utils import make_logger
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
        self.lobby_buttons = []
        self.lobbyframe = tk.Frame(self)
        self.make_client_list(self.lobbyframe)
        self.gamesframe = tk.Frame(self)
        self.buttonframe = tk.Frame(self.gamesframe)
        actions = [("Join game",self.join_game),("Host game",self.host_game)]
        for b_label,b_action in actions:
            b = tk.Button(self.buttonframe,text=b_label,command=b_action)
            self.lobby_buttons.append(b)
        self.game_name_label = tk.Label(self.buttonframe,text='Game name:')
        self.game_name_entry = tk.Entry(self.buttonframe)

    def show_lobby(self):
        self.connector.request_playerlist()
        self.lobbyframe.pack(fill=tk.Y,side=tk.LEFT)
        self.gamesframe.pack(fill=tk.X,expand=1,side=tk.LEFT, anchor=tk.N)
        self.buttonframe.pack(fill=tk.X,expand=1,side=tk.LEFT)
        for button in self.lobby_buttons:
            button.pack(fill=tk.X, side=tk.LEFT,expand=1)
        self.game_name_label.pack(fill=tk.X,side=tk.LEFT,expand=1)
        self.game_name_entry.pack(fill=tk.X,side=tk.LEFT,expand=1)

    def make_client_list(self,master):
        self.clients = [self.username]
        self.client_list_label = tk.Label(master,text='Lobby:',pady=5)
        self.client_list = tk.Listbox(master)
        self.client_list_label.pack(anchor=tk.NW)
        self.client_list.pack(fill=tk.Y,expand=1,anchor=tk.NW)

    def hide_lobby(self):
        self.lobbyframe.pack_forget()

    def hide_server_selection(self):
        self.server_selection_frame.pack_forget()

    def join_game(self):
        print "Dummy!"

    def host_game(self):
        print "Dummy!"

    def update_server_box(self,serv_name,add):
        self.update_listbox(self.server_box,serv_name,add)
        if self.server_box.size() == 1:
            self.server_box.select_set(0)

    def update_client_box(self,client_name,add):
        self.update_listbox(self.client_list,client_name,add)

    def update_listbox(self,listbox,name,add):
        if add:
            for i in range(listbox.size()):
                if name == listbox.get(i):
                    return
            listbox.insert(tk.END,name)
        else:
            for i in range(listbox.size()):
                val = listbox.get(i)
                if name == val:
                    listbox.delete(i)
                    return

    def pick_server(self):
        selected = self.server_box.curselection()
        uname = self.username_entry.get()
        if selected and uname:
            serv_name = selected[0]
            self.connector.join_server(self.server_box.get(serv_name),uname)
            self.hide_server_selection()

    def disconnect(self):
        self.connector.disconnect()

app = ClientApplication()
app.master.title("Battleship 2016")
app.mainloop()
app.disconnect()
