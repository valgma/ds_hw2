#!/usr/bin/env python
from utils import make_logger
import Tkinter as tk
import ttk
from clientconnector import ClientConnector
from server import Server

Log = make_logger()

#TODO: Don't allow ":" in names

class ClientApplication(tk.Frame):
    def __init__(self,master=None,host='localhost'):
        tk.Frame.__init__(self,master)
        self.pikahost = host
        self.create_widgets()
        self.connector = ClientConnector(host,self)
        self.server = None
        self.connector.setDaemon(True)
        self.connector.start()
        self.username = ""

    def create_widgets(self):
        #usernames are specified for both client and server
        self.username_label = tk.Label(self,text='Username')
        self.username_label.pack()
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()

        #General connecting widget
        self.nb = ttk.Notebook(self)
        self.nb.pack(expand=True,fill=tk.X)


        # ---------- Client tab widgets ----------
        self.client_tab = tk.Frame(self)
        self.nb.add(self.client_tab,text='Join game')

        #server selection area
        self.servers = []
        self.server_box_label = ttk.Label(self.client_tab,
                                          text="Available servers:")
        self.server_box = tk.Listbox(self.client_tab)

        self.server_box_label.pack()
        self.server_box.pack()

        self.server_button = tk.Button(self.client_tab,
                                        text="Connect",
                                        command=self.pick_server)
        self.server_button.pack()

        # ---------- Server tab widgets ----------
        self.server_tab = tk.Frame(self)
        self.nb.add(self.server_tab,text='Host game')

        self.server_name_label = tk.Label(self.server_tab,
                                            text='Server name')
        self.server_name_label.pack()

        self.server_name_entry = tk.Entry(self.server_tab)
        self.server_name_entry.pack()

        self.host_button = tk.Button(self.server_tab,
                                    text="Start server",
                                    command=self.host_server)
        self.host_button.pack()

        self.pack()

    def host_server(self):
        server_name = self.server_name_entry.get()
        user_name = self.username_entry.get()

        #TODO: Find a nicer way to make exclusive server names
        #or handle exchanges differently.
        if server_name and user_name and server_name not in self.servers:
            self.nb.tab(self.client_tab,state=tk.DISABLED)
            #TODO: Make your own name editing inactive or something
            self.host_button.pack_forget()
            self.server_name_entry.pack_forget()
            self.server_name_label.pack_forget()

            self.username = user_name
            self.make_client_list(self.server_tab)


            self.server = Server(self.pikahost,server_name,user_name,self)
            self.server.setDaemon(True)
            self.server.start()





    def make_client_list(self,master):
        self.clients = [self.username]
        self.client_list_label = tk.Label(master,text='Players:')
        self.client_list = tk.Listbox(master)
        self.client_list.insert(tk.END,self.username)
        self.client_list_label.pack()
        self.client_list.pack()

    def show_lobby(self):
        self.make_client_list(self)
        self.connector.request_playerlist()


    #TODO: Merge these two together. tomorrow...
    def update_server_box(self,serv_name,add):
        if add and serv_name not in self.servers:
            self.servers.append(serv_name)
            self.server_box.insert(tk.END,serv_name)
        elif not add and serv_name in self.servers:
            ind = self.servers.index(serv_name)
            self.server_box.delete(ind)
            del self.servers[ind]

    def update_client_box(self,client_name,add):
        if add and client_name not in self.clients:
            self.client_list.insert(tk.END,client_name)
            self.clients.append(client_name)
        elif not add and client_name in self.clients:
            index = self.clients.index(client_name)
            del self.client_list[index]

    def pick_server(self):
        selected = self.server_box.curselection()
        uname = self.username_entry.get()
        if selected and uname:
            serv_name = selected[0]
            self.connector.join_server(self.server_box.get(serv_name),uname)
            self.hide_lobby()

    def hide_lobby(self):
        self.nb.pack_forget()
        self.username_entry.pack_forget()
        self.username_label.pack_forget()

    def disconnect(self):
        if self.server:
            self.server.disconnect()
        self.connector.disconnect()

app = ClientApplication()
app.master.title("Battleship 2016")
app.mainloop()
app.disconnect()
