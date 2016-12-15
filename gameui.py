from utils import make_logger
from gamebox import Gamebox
import mtTkinter.mtTkinter as tk
import Pyro4
import tkFont

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
        if self.leader == self.gamebox.my_name and self.gamebox.gamestate.get_game_on():
            self.gamebox.gamestate.switch_turn()
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
        self.clear_colours()
        self.colour_turn(self.leader)
        self.gamebox.rcv_start()


    def connect_state(self,uri):
        if not self.gamestate:
            self.gamestate = Pyro4.Proxy(uri)
            self.make()
            self.show_boxes()
            for i in self.gamestate.testmethod():
                print i

    def promote_to_leader(self,leader):
        if self.leader:
            self.update_playercolour(self.leader,'white')
        self.leader = leader
        self.update_playercolour(self.leader)
        if leader == self.root.username:
            self.gamebox.add_leader_button()
        #TODO: if leadership changes, change the button back (self.gamebox.remove_leader_button())
        self.update_playercolour(leader)

    def update_playercolour(self,player,colour='pale green'):
        try:
            ind = self.players.get(0,tk.END).index(player)
            self.players.itemconfig(ind,bg=colour)
        except Exception as e:
            Log.debug("Couldn't change colour of %r.", player)
            return

    def clear_colours(self):
        playerlist = self.players.get(0,tk.END)
        for ind, player_name in enumerate(playerlist):
            if player_name != self.leader:
                self.players.itemconfig(ind,bg='white')
            else:
                self.players.itemconfig(ind,bg='pale green')

    def colour_turn(self,name):
        self.clear_colours()
        colour = 'red' if self.leader == name else 'orange'
        self.update_playercolour(name,colour)

    def rem_player(self,name):
        try:
            ind = self.players.get(0,tk.END).index(name)
            self.players.delete(ind)
            self.gamebox.remove_field(name)
            self.gamebox.gamestate.remove_player(name)
            players = self.gamebox.gamestate.list_players()
            if self.gamebox.gamestate.get_game_on():
                self.gamebox.switch_turn()
            if len(players) < 2 and self.gamebox.gamestate.get_game_on():
                print "GAME OVER"
                #TODO: only 1 player - kick everybody out
            else:
                self.notify_players("game.leader", list(players)[0])
        except Exception as e:
            return
