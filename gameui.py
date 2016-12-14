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
        self.gamestate = None
        self.gamebox = None
        self.connector.request_uri()
        self.leader = ""

    def notify_players(self,key,message,props=None):
        self.connector.notify_exchange(self.connector.room_name,key,message,props)

    def make(self):
        self.infobox = tk.Frame(self)
        self.gamebox = Gamebox(self, self.root.username, None, {}) # TODO!
        self.quitbutton = tk.Button(self.infobox,text='Leave game',bg='tomato',command=self.leave_game)
        self.players = tk.Listbox(self.infobox)
        self.connector.get_game_players()

    def show(self):
        self.pack(fill=tk.BOTH,expand=1)

    def show_boxes(self):
        self.infobox.pack(side=tk.LEFT,fill=tk.Y)
        self.gamebox.pack(side=tk.TOP,fill=tk.BOTH,anchor=tk.N)
        self.quitbutton.pack(fill=tk.X)
        self.players.pack(fill=tk.Y,expand=1)

    def leave_game(self):
        self.root.abandon_game()
        self.connector.leave_game()
        self.gamebox.gamestate.remove_player(self.gamebox.my_name)

    def add_player(self,name):
        if name not in self.players.get(0,tk.END):
            self.players.insert(tk.END,name)
            if self.gamebox:
                self.gamebox.add_empty_field(name)
                if self.gamebox.my_name == name:
                    self.gamebox.enable_field(name)
                else:
                    self.gamebox.disable_field(name)
                self.gamebox.gamestate.add_player(name)

    #def switch_turn(self, msg):
    def fire(self, msg):
        pieces = msg.split("/")
        src_name = pieces[0]
        tgt_name = pieces[1]
        row = int(pieces[2])
        col = int(pieces[3])
        self.gamebox.rcv_fire(src_name, tgt_name, row, col)
        #self.gamebox.switch_turn()

    def start_game(self):
        self.gamebox.rcv_start()


    def connect_state(self,uri):
        if not self.gamestate:
            self.gamestate = Pyro4.Proxy(uri)
            self.make()
            self.show_boxes()
            for i in self.gamestate.testmethod():
                print i

    def promote_to_leader(self,leader):
        if leader == self.root.username:
            self.gamebox.add_leader_button()
        #TODO: if leadership changes, change the button back (self.gamebox.remove_leader_button())
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
            self.gamebox.remove_field(name)
            self.gamebox.gamestate.remove_player(name)
            players = self.gamebox.gamestate.list_players()
            if len(players) < 2:
                print "GAME OVER"
                #TODO: only 1 player - kick everybody out
            else:
                self.notify_players("game.leader", list(players)[0])
        except Exception as e:
            return
