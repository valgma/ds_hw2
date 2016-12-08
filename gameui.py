from utils import make_logger
import Tkinter as tk

Log = make_logger()

class GameUI(tk.Frame):
    def __init__(self,master,cnn):
        tk.Frame.__init__(self,master)
        self.connector = cnn
        self.root = master
        self.make()

    def make(self):
        self.infobox = tk.Frame(self)
        self.gamebox = tk.Frame(self)
        self.l = tk.Label(self.gamebox,text="GAME GOES HERE")
        self.quitbutton = tk.Button(self.infobox,text='Leave game',bg='tomato',command=self.leave_game)
        self.players = tk.Listbox(self.infobox)

    def show(self):
        self.pack(fill=tk.BOTH,expand=1)
        self.infobox.pack(side=tk.LEFT,fill=tk.Y)
        self.gamebox.pack(side=tk.TOP,fill=tk.BOTH,anchor=tk.N)
        self.quitbutton.pack(fill=tk.X)
        self.players.pack(fill=tk.Y,expand=1)
        self.l.pack()

    def leave_game(self):
        self.connector.leave_game()
        self.root.abandon_game()

    def add_player(self,name):
        if name not in self.players.get(0,tk.END):
            self.players.insert(tk.END,name)

    def rem_player(self,name):
        try:
            ind = self.players.get(0,tk.END).index(name)
            self.players.delete(ind)
        except Exception as e:
            return
