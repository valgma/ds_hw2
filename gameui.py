from utils import make_logger
from gamebox import Gamebox
import mtTkinter.mtTkinter as tk
import Pyro4

Log = make_logger()

class GameUI(tk.Frame):
    def __init__(self,master,cnn):
        tk.Frame.__init__(self,master)
        self.connector = cnn
        self.root = master
        self.make()
        self.gamestate = None
        self.connector.request_uri()
        self.leader = ""

    def make(self):
        self.infobox = tk.Frame(self)
        self.gamebox = Gamebox(self, self.root.username, None, {}) # TODO!
        self.quitbutton = tk.Button(self.infobox,text='Leave game',bg='tomato',command=self.leave_game)
        self.players = tk.Listbox(self.infobox)
        self.connector.get_game_players()

    def show(self):
        self.pack(fill=tk.BOTH,expand=1)
        self.infobox.pack(side=tk.LEFT,fill=tk.Y)
        self.gamebox.pack(side=tk.TOP,fill=tk.BOTH,anchor=tk.N)
        self.quitbutton.pack(fill=tk.X)
        self.players.pack(fill=tk.Y,expand=1)

    def leave_game(self):
        self.root.abandon_game()
        self.connector.leave_game()


    def add_player(self,name):
        if name not in self.players.get(0,tk.END):
            self.players.insert(tk.END,name)

    def connect_state(self,uri):
        if not self.gamestate:
            self.gamestate = Pyro4.Proxy(uri)
            for i in self.gamestate.testmethod():
                print i

    def promote_to_leader(self,leader):
        self.update_leadercolour(leader)

    def update_leadercolour(self,leader,colour='pale green'):
        if self.leader:
            old_leader = self.leader
            self.leader = ""
            self.update_leadercolour(old_leader,'white')
        try:
            sisu = self.players.get(0,tk.END)
            ind = self.players.get(0,tk.END).index(leader)
            self.players.itemconfig(ind,bg=colour)
            self.leader = leader
        except Exception as e:
            Log.debug("Couldn't mark/unmark %r as leader.", leader)
            return

    def rem_player(self,name):
        try:
            ind = self.players.get(0,tk.END).index(name)
            self.players.delete(ind)
        except Exception as e:
            return
