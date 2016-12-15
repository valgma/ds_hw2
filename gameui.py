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

    # function for sending a message to all other players
    def notify_players(self,key,message,props=None):
        self.connector.notify_exchange(self.connector.room_name,key,message,props)

    # initializing fields
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

    # function for leaving the game
    def leave_game(self):
        # if we are the leader and the game is running, switch turns
        if self.leader == self.gamebox.my_name and self.gamebox.gamestate.get_game_on():
            self.gamebox.gamestate.switch_turn()
        self.root.abandon_game()
        self.connector.leave_game()
        # remove the player from Gamestate
        self.gamebox.gamestate.remove_player(self.gamebox.my_name)

    # function for adding a player with a given name
    def add_player(self,name):
        pl = self.players.get(0,tk.END)
        if name not in pl:
            # adding the name to the box with players' names
            self.players.insert(tk.END,name)
            if self.gamebox:
                # creating an empty board for that player
                self.gamebox.add_empty_field(name)
                # if we are that player, we enable that board (to position ships)
                if self.gamebox.my_name == name:
                    self.gamebox.enable_field(name)
                # otherwise disable it (to prevent from firing)
                else:
                    self.gamebox.disable_field(name)
                # saving that player in Gamestate
                self.gamebox.gamestate.add_player(name)
        else:
            ind = pl.index(name)
            self.players.itemconfig(ind,fg='black')

    def rejoin(self):
        self.gamebox.resume()

    # function for after receiving a message about firing
    def fire(self, msg):
        # parsing the message for the source, target, row and column of the firing
        pieces = msg.split("/")
        src_name = pieces[0]
        tgt_name = pieces[1]
        row = int(pieces[2])
        col = int(pieces[3])
        # handling the results of the firing
        self.gamebox.rcv_fire(src_name, tgt_name, row, col)

    # function for skipping a turn
    def skip(self):
        self.gamebox.skip()

    # function for starting a game
    def start_game(self):
        self.clear_colours()
        self.colour_turn(self.leader)
        # handling the start of the game
        self.gamebox.rcv_start()


    def connect_state(self,uri):
        if not self.gamestate:
            self.gamestate = Pyro4.Proxy(uri)
            self.make()
            self.show_boxes()
            for i in self.gamestate.testmethod():
                print i

    # function for giving a player leader rights
    def promote_to_leader(self,leader):
        if self.leader:
            self.update_playercolour(self.leader,'white')
        # marking him as leader
        self.leader = leader
        self.update_playercolour(self.leader)
        # if we are the leader
        if leader == self.root.username:
            # add the "Start game" button (instead of "Ready" button)
            self.gamebox.add_leader_button()
            # if ships have not been confirmed, grant rights to confirm them
            if not self.gamebox.gamestate.are_ships_confirmed():
                self.gamebox.add_ship_confirm()
                self.gamebox.update_ship_label()
        self.update_playercolour(leader)

    # colouring a player with a specific colour (green by default) in the players' box
    def update_playercolour(self,player,colour='pale green'):
        try:
            ind = self.players.get(0,tk.END).index(player)
            self.players.itemconfig(ind,bg=colour)
        except Exception as e:
            Log.debug("Couldn't change colour of %r.", player)
            return

    # replacing the orange/red colour in the players' box with white/gray, depending on leadership
    def clear_colours(self):
        playerlist = self.players.get(0,tk.END)
        for ind, player_name in enumerate(playerlist):
            if player_name != self.leader:
                self.players.itemconfig(ind,bg='white')
            else:
                self.players.itemconfig(ind,bg='pale green')

    # colouring a given name red in the players' box
    def colour_name_red(self,name):
        try:
            ind = self.players.get(0,tk.END).index(name)
            self.players.itemconfig(ind,fg='red')
        except Exception as e:
            Log.debug("Couldn't change colour of %r.", name)
            return

    # colouring a given name (the player whose turn it is to fire) orange in the players' box
    def colour_turn(self,name):
        self.clear_colours()
        colour = 'red' if self.leader == name else 'orange'
        self.update_playercolour(name,colour)

    # removing a player from the game
    def rem_player(self,name):
        try:
            # deleting the player from the players' box
            ind = self.players.get(0,tk.END).index(name)
            self.players.delete(ind)
            # deleting the player's board
            self.gamebox.remove_field(name)
            # deleting him from Gamestate.players (basically going into spectator mode)
            self.gamebox.gamestate.remove_player(name)
            players = self.gamebox.gamestate.list_players()
            #if len(players) < 2 and self.gamebox.gamestate.get_game_on():
                #TODO: only 1 player - kick everybody out
            # if the game is still running, update the labels in case of switched turns
            if self.gamebox.gamestate.get_game_on():
                self.gamebox.switch_turn()
        except Exception as e:
            return
