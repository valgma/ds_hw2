import string

import mtTkinter.mtTkinter as tk
from random import randint
from utils import make_logger, validate_ships

SHIP_COL = 'gray80'
CELL_EMPTY = 0
CELL_SHIP = 1
CELL_HIT = 2
CELL_MISS = 3
CELL_CRASH = 4

Log = make_logger()

class Gamebox(tk.Frame):

    box_edge = 20  # len of one box on field

    def __init__(self, master, my_name, my_field, other_fields):
        # my_field - rows x cols matrix
        # other_fileds - name: field dictionary
        tk.Frame.__init__(self, master)
        self.my_name = my_name
        self.gamestate = master.gamestate
        board_size = self.gamestate.get_board_size()
        self.rows = board_size
        self.cols = board_size
        self.last_click_loc = (None, None, None)  # name, row, col
        self.clicks_set = set() # holds any number of clicks, could be used to mark ships
        self.message_label = None

        # make sure we have a field to draw
        tmp_field = my_field
        if not tmp_field:
            tmp_field = [[0] * self.cols] * self.rows

        self.my_canvas = GameCanvas(self, self.box_edge, self.rows, self.cols, tmp_field, my_name)
        self.my_canvas.grid(row=0, columnspan=2)

        self.other_canvases = {}
        for name, field in other_fields.iteritems():
            self.other_canvases[name] = GameCanvas(self, self.box_edge, self.rows, self.cols, field, name)

        self.draw_fields()

        # buttons in a separate frame
        self.button_frame = tk.Frame(self)
        self.button_frame.grid(row=0, column=2)
        #self.entry_input = tk.Entry(self.button_frame)
        #self.entry_input.grid(row=0, column=0)
        self.startbutton = tk.Button(self.button_frame, text='Ready', command=self.ready)
        self.startbutton.grid(row=1, column=0)
        self.message_label = tk.Label(self.button_frame, text="Position your ships!")
        self.message_label.grid(row=2, column=0)

    def start_game(self):
        ready = self.validate_ships()
        ready_players_count = self.gamestate.get_ready_players_count()
        if ready and ready_players_count >= 1:
            self.gamestate.init_turns(self.my_name)
            #TODO: start game with the players who are ready
            self.message_label.config(text="Game begins. Your turn.")
            ships = self.get_clicks(self.my_name)
            self.gamestate.add_board(self.my_name, ships)
            self.gamestate.add_other_players_boards()
            self.enable_all_fields()
            self.disable_field(self.my_name)
            self.startbutton.config(state='disabled')
        elif ready:
            self.message_label.config(text="Not enough players to start.")
        else:
            self.message_label.config(text="Validation failed.")
        #TODO: lock positioning ships, lock joining the game

    def ready(self):
        if self.validate_ships():
            self.gamestate.set_ready(self.my_name)
            self.message_label.config(text="You're ready")
            ships = self.get_clicks(self.my_name)
            self.gamestate.add_board(self.my_name, ships)
            self.disable_all_fields()
            self.disable_field(self.my_name)
            self.startbutton.config(state='disabled')
        else:
            self.message_label.config(text="Validation failed.")

    def fire(self, src_name, tgt_name, row, column):
        boards = self.gamestate.get_boards()
        other_players_boards = self.gamestate.get_other_players_boards()
        src_other_players_boards = other_players_boards[src_name]
        cell_value = boards[tgt_name][row][column]
        if cell_value == 0:                                                         # empty cell
            src_other_players_boards[tgt_name][row][column] = 3
            self.message_label.config(text="You missed!")
            #TODO: message to tgt that we missed
        elif cell_value == 1:                                                       # ship
            boards[tgt_name][row][column] = 2
            self.message_label.config(text="You hit!")
            ship_cells = self.gamestate.get_ship_cells(tgt_name, row, column)
            if all(boards[tgt_name][r][c] == 2 for (r, c) in ship_cells):           # ship sinks
                self.message_label.config(text="You sunk a ship!")
                players = self.gamestate.list_players()
                for p in players:
                    if p != tgt_name:
                        for (r, c) in ship_cells:
                            other_players_boards[p][tgt_name][r][c] = 4
                #TODO: message to all that this ship has sunk
        self.gamestate.switch_turn()
        self.master.notify_players('game.turn','')


    def switch_turn(self):
        turn = self.gamestate.get_turn()
        print "Here, I am", self.my_name, "it's ", turn, "'s turn."
        #self.gamestate.switch_turn()
        if turn == self.my_name:
            self.message_label.config(text="Your turn!")
            self.enable_all_fields()
        else:
            last_turn = self.gamestate.get_last_turn()
            if self.my_name == last_turn:
                self.message_label.config(text=(self.message_label.cget("text") + "\nWaiting for player " + turn))
            else:
                self.message_label.config(text="Waiting for player " + turn)
            self.disable_all_fields()
        #TODO: repaint cells

    #def repaint(self): #TODO


    def add_leader_button(self):
        self.startbutton.config(text='Start game', command=self.start_game)

    def remove_leader_button(self):
        self.startbutton.config(text='Ready', command=self.ready)
        self.startbutton.grid(row=1, column=0)


    # draws other players fields, 3 fields in a row
    def draw_fields(self):
        for name, canvas in self.other_canvases.iteritems():
            self.other_canvases[name].grid_remove()

        i = 0
        for name, canvas in self.other_canvases.iteritems():
            row_idx = int(i / 3) + 1
            col_idx = i % 3
            self.other_canvases[name].grid(row=row_idx, column=col_idx)
            i += 1

    # for testing
    def enable_named_field(self, name):
        self.enable_field(name)

    # for testing
    def disable_named_field(self, name):
        self.disable_field(name)

    # for testing
    def remove_named_field(self):
        sel_name = self.entry_input.get()
        self.remove_field(sel_name)

    # for testing
    def add_random_field(self):
        name = self.entry_input.get()
        field = [[randint(0, 5) for _ in range(self.rows)] for _ in range(self.cols)]
        self.add_field(name, field)

    def add_empty_field(self, name):
        field = [[0 for _ in range(self.rows)] for _ in range(self.cols)]
        self.add_field(name, field)

    def add_field(self, name, field):
        if name not in self.other_canvases and name != self.my_name:
            self.other_canvases[name] = GameCanvas(self, self.box_edge, self.rows, self.cols, field, name)
            row_idx = int((len(self.other_canvases)-1) / 3) + 1
            col_idx = (len(self.other_canvases)-1) % 3
            self.other_canvases[name].grid(row=row_idx, column=col_idx)
        else:
            Log.debug('Already has player named %s' % str(name))

    def remove_field(self, name):
        if name in self.other_canvases:
            self.other_canvases[name].grid_remove()
            self.other_canvases[name].destroy()
            del self.other_canvases[name]
            self.draw_fields()
        else:
            Log.debug('Do not have player named %s' % str(name))

    def draw_miss(self, name, row, col):
        if name == self.my_name:
            self.my_canvas.draw_miss(row, col)
        elif name in self.other_canvases:
            self.other_canvases[name].draw_miss(row, col)
        else:
            Log.debug('Do not have player %s' % name)

    def draw_hit(self, name, row, col):
        if name == self.my_name:
            self.my_canvas.draw_hit(row, col)
        elif name in self.other_canvases:
            self.other_canvases[name].draw_hit(row, col)
        else:
            Log.debug('Do not have player %s' % name)

    def draw_crash(self, name, row, col):
        if name == self.my_name:
            self.my_canvas.draw_crash(row, col)
        elif name in self.other_canvases:
            self.other_canvases[name].draw_crash(row, col)
        else:
            Log.debug('Do not have player %s' % name)

    def enable_field(self, name):
        if name == self.my_name:
            self.my_canvas.enable_input()
        elif name in self.other_canvases:
            self.other_canvases[name].enable_input()
        else:
            Log.debug('Do not have player %s' % name)

    def disable_field(self, name):
        if name == self.my_name:
            self.my_canvas.disable_input()
        elif name in self.other_canvases:
            self.other_canvases[name].disable_input()
        else:
            Log.debug('Do not have player %s' % name)

    def enable_all_fields(self):
        for name in self.other_canvases:
            self.enable_field(name)

    def disable_all_fields(self):
        for name in self.other_canvases:
            self.disable_field(name)

    def set_last_click(self, name, row, col):
        self.last_click_loc = name, row, col
        if self.last_click_loc not in self.clicks_set:
            self.clicks_set.add(self.last_click_loc)
            if name == self.my_name:
                self.my_canvas.draw_rec(row, col, SHIP_COL)
        else:
            self.clicks_set.remove(self.last_click_loc)
            if name == self.my_name:
                self.my_canvas.draw_rec(row, col, 'SystemButtonFace')

    def get_last_click(self):
        return self.last_click_loc

    def clear_clicks(self):
        self.clicks_set.clear()

    def get_clicks(self, field_name):
        field = []
        for name, row, col in self.clicks_set:
            if name == field_name:
                field.append((row, col))
        return field

    def print_ships(self):
        print self.get_clicks(self.my_name)

    def validate_ships(self):
        ships = self.get_clicks(self.my_name)
        return validate_ships(ships, self.rows, self.cols)

class GameCanvas(tk.Canvas):
    def __init__(self, master, box_edge, rows, cols, field, name):
        self.root = master
        self.box_edge = box_edge
        self.rows = rows
        self.cols = cols
        self.field = field
        self.name = name
        self.w, self.h = self.box_edge * (self.cols+1), self.box_edge * (self.rows+1) + 30

        tk.Canvas.__init__(self, master, width=self.w, height=self.h)

        self.create_text((int(cols*box_edge/2), self.box_edge * (self.rows+1)+15), text=self.name)

        # draw grid
        for row in range(self.rows + 2):
            self.create_line(0, row * self.box_edge, self.w, row * self.box_edge)
        for col in range(self.cols + 2):
            self.create_line(col * self.box_edge, 0,  col * self.box_edge, self.h-30)

        # make row headings
        for row in range(1, self.rows + 1):
            x0 = self.box_edge / 2
            y0 = row * self.box_edge + self.box_edge / 2
            self.create_text((x0, y0), text=str(row))

        # make col headings
        for col in range(1, self.cols + 1):
            y0 = self.box_edge / 2
            x0 = col * self.box_edge + self.box_edge / 2
            lbl = string.ascii_uppercase[col - 1]
            self.create_text((x0, y0), text=lbl)

        # draw current field
        for row, row_content in enumerate(self.field):
            for col, c in enumerate(row_content):
                if c == CELL_SHIP:
                    self.draw_rec(row, col, SHIP_COL)
                elif c == CELL_HIT or c == CELL_CRASH:
                    self.draw_hit(row, col)
                elif c == CELL_MISS:
                    self.draw_miss(row, col)

    def draw_miss(self, row, col):
        self.draw_x(row, col)

    def draw_hit(self, row, col):
        self.draw_rec(row, col, SHIP_COL)
        self.draw_x(row, col)

    def draw_crash(self, row, col):
        self.draw_x(row, col)

    def draw_rec(self, row, col, color):
        x0 = (col+1) * self.box_edge
        y0 = (row+1) * self.box_edge
        self.create_rectangle((x0, y0, x0+self.box_edge, y0+self.box_edge), fill=color)

    def draw_x(self, row, col, color='black'):
        x0 = (col+1) * self.box_edge
        y0 = (row+1) * self.box_edge
        self.create_line(x0, y0, x0+self.box_edge, y0+self.box_edge, fill=color)
        self.create_line(x0, y0+self.box_edge, x0+self.box_edge, y0, fill=color)

    def enable_input(self):
        # bind mouseclick
        self.bind("<Button-1>", self.canvas_mouseclick)
        self.draw_rec(-1, -1, 'green')

    def disable_input(self):
        self.unbind("<Button-1>")
        self.draw_rec(-1, -1, 'SystemButtonFace')

    def canvas_mouseclick(self, event):
        x, y = event.x, event.y
        row = int(y / self.box_edge - 1)
        col = int(x / self.box_edge - 1)
        self.root.set_last_click(self.name, row, col)
        print str(self.name) + ": " + '%d %d' % (row, col)
        if self.master.my_name != self.name:
            self.master.fire(self.master.my_name, self.name, row, col)

if __name__ == '__main__':
    my_game = [[0 for _ in range(10)] for _ in range(10)]
    other_games = {str(i):[[randint(0, 5) for _ in range(10)] for _ in range(10)] for i in range(2)}

    root = tk.Tk()
    root.title("Blah blah")
    mainframe = Gamebox(root, 'myself', 10, my_game, other_games)
    mainframe.grid(sticky=(tk.N, tk.W, tk.E, tk.S))

    root.mainloop()