import string

import mtTkinter.mtTkinter as tk
from random import randint
from utils import make_logger, validate_ships

SHIP_COL = 'gray80'
SEA_COL = 'light sky blue'
CRASH_COL = 'red'
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
        self.resetbutton = tk.Button(self.button_frame, text='Restart game', command=self.restart_game)
        self.resetbutton.grid(row=3, column=0)
        self.resetbutton.grid_forget()
        self.message_label = tk.Label(self.button_frame, text="Position your ships!")
        self.message_label.grid(row=2, column=0)
        self.ships_label = tk.Label(self.button_frame)
        self.ships_label.grid(row=4,column=0)
        self.update_ship_label()

        # separate frame for the leader for providing the number of ships per length

        self.ship_frame = tk.Frame(self)
        self.ship2_input = tk.Entry(self.ship_frame)
        self.ship3_input = tk.Entry(self.ship_frame)
        self.ship4_input = tk.Entry(self.ship_frame)
        self.ship5_input = tk.Entry(self.ship_frame)
        self.ship2_label = tk.Label(self.ship_frame, text="x 2 ships")
        self.ship3_label = tk.Label(self.ship_frame, text="x 3 ships")
        self.ship4_label = tk.Label(self.ship_frame, text="x 4 ships")
        self.ship5_label = tk.Label(self.ship_frame, text="x 5 ships")
        self.ship_button = tk.Button(self.ship_frame, text="Confirm ships", command=self.confirm_ships)
        self.ship2_input.grid(row=0, column=0)
        self.ship3_input.grid(row=1, column=0)
        self.ship4_input.grid(row=2, column=0)
        self.ship5_input.grid(row=3, column=0)
        self.ship2_label.grid(row=0, column=1)
        self.ship3_label.grid(row=1, column=1)
        self.ship4_label.grid(row=2, column=1)
        self.ship5_label.grid(row=3, column=1)
        self.ship_button.grid(row=4, column=0)
        self.ship_frame.grid_forget()

    # function for setting the text for ship_label, depending on whether the ships have been confirmed or not, and leader status
    def update_ship_label(self):
        if self.my_name == self.master.leader:
            self.ships_label.config(text="Confirm ships!")
        else:
            if self.gamestate.are_ships_confirmed():
                self.rcv_game_configure()
            else:
                self.ships_label.config(text="Leader is still confirming ships.")

    # getting the ship data, saving it in Gamestate and notifying others
    def confirm_ships(self):
        #retrieving the data for ships from the entry slots
        ship2 = self.ship2_input.get()
        ship3 = self.ship3_input.get()
        ship4 = self.ship4_input.get()
        ship5 = self.ship5_input.get()
        if ship2.isdigit() and ship2.isdigit() and ship4.isdigit() and ship5.isdigit():
            # saving the data in Gamestate
            self.gamestate.add_req_ships(int(ship2), int(ship3), int(ship4), int(ship5))
            # hiding the ship confirmation section
            self.ship_frame.grid_forget()
            # notifying other players about the numbers of ships (per length) to be added to the board
            self.master.notify_players("game.configure", "")

    # updating the ship_label with correct numbers after receiving a message that ships have been confirmed by the leader
    def rcv_game_configure(self):
        # getting the data from Gamestate
        ship2 = self.gamestate.get_ship_count(2)
        ship3 = self.gamestate.get_ship_count(3)
        ship4 = self.gamestate.get_ship_count(4)
        ship5 = self.gamestate.get_ship_count(5)
        #updating the label
        self.ships_label.config(text=str(ship2) + "x2 ships\n" + str(ship3) + "x3 ships\n" +str(ship4) + "x4 ships\n" +str(ship5) + "x5 ships")

    # adding the ship confirmation section to the game leader's window
    def add_ship_confirm(self):
        self.ship_frame.grid(row=0, column=3)

    # leader initializes the game
    def start_game(self):
        # checking whether the ships have been positioned correctly
        ready = self.validate_ships()
        if ready:
            # marking the state as "ready" in Gamestate
            self.gamestate.set_ready(self.my_name)
            ready_players_count = self.gamestate.get_ready_players_count()
            # if there are at least two players, the game can start
            if ready_players_count >= 2:
                #TODO: start game with only the players who are ready, kick others out - done, but there's some bug
                # initializing turns (in which order players fire - starting always from the leader)
                self.gamestate.init_turns(self.my_name)
                # getting the locations for ships we positioned
                ships = self.get_clicks(self.my_name)
                # initializing fields for storing our own board and everybody else's boards from our point of view
                self.gamestate.add_board(self.my_name, ships)
                self.gamestate.add_other_players_boards()
                # disabling the "Start game" button
                self.startbutton.config(state="disabled")
                self.gamestate.set_game_on(True)
                # notifyin other players that the game started
                self.master.notify_players("game.start", "")
            else:
                self.message_label.config(text="Not enough players to start.")
        else:
            self.message_label.config(text="Ship validation failed.")

    # function for after having received the message "game.start"
    def rcv_start(self):
        # if we are not ready (didn't position our ships and click "Ready"/"Start game"), we leave the game
        if not self.gamestate.is_ready(self.my_name):
            self.master.leave_game()
        # getting whose turn it is to fire
        turn = self.gamestate.get_turn()
        # if it's our turn, we enable all other players' boards for us to fire at
        if turn == self.my_name:
            self.message_label.config(text="Game begins. Your turn.")
            self.enable_all_fields()
            self.disable_field(self.my_name)
        # otherwise we disable all fields for firing
        else:
            self.message_label.config(text="Game begins. Waiting for " + turn + ".")
            self.disable_all_fields()

    # function for firing at a certain cell of a certain target's board
    def fire(self, src_name, tgt_name, row, col):
        boards = self.gamestate.get_boards()
        # the real value of that cell we fired at
        cell_value = boards[tgt_name][row][col]
        # if that cell contained a ship and nobody had hit that cell yet
        if cell_value == 1:                                         # hit a ship
            # we update it in Gamestate and mark it as "hit"
            self.gamestate.update_boards(tgt_name, row, col, 2)
            # getting all the cells of that particular ship
            ship_cells = self.gamestate.get_ship_cells(tgt_name, row, col)
            # checking if all cells have been hit and thus the ship sinks
            if self.ship_shinks(tgt_name, ship_cells):              # ship sinks
                players = self.gamestate.list_players()
                for p in players:
                    if p != tgt_name:
                        for (r, c) in ship_cells:
                            # marking the whole ship as sunk, so that everybody can see it
                            self.gamestate.update_boards(tgt_name, r, c, 4)
        # passing the turn to fire on to the next player
        self.gamestate.switch_turn()
        # sending a message to all players that src_name fired at tgt_name's cell with the location (row, col)
        self.master.notify_players('game.fire',src_name + "/" + tgt_name + "/" + str(row) + "/" + str(col))

    def skip(self):
        self.switch_turn()
    # function for after receiving a message that src_name fired at tgt_name's cell with the location (row, col)
    # here we update our boards and react if somebody won or lost
    def rcv_fire(self, src_name, tgt_name, row, col):
        board = self.gamestate.get_board(tgt_name)
        # the corresponding cell value of the target
        value = board[row][col]
        #if we are the ones who fired
        if self.my_name == src_name:
            # if we missed, we update our target's board in our window and draw a cross there
            if value == 0:
                self.message_label.config(text="You missed " + tgt_name + "'s ship!")
                self.gamestate.update_other_players_boards(src_name, tgt_name, row, col, 3)
                self.draw_miss(tgt_name, row, col)
            # if we hit a ship (but didn't sink it), we draw a ship and a cross
            elif value == 2:
                self.message_label.config(text="You hit " + tgt_name + "'s ship!")
                self.gamestate.update_other_players_boards(src_name, tgt_name, row, col, 2)
                self.draw_hit(tgt_name, row, col)
            # if we sunk that ship, we make the whole ship red
            elif value == 4:
                self.message_label.config(text="You sunk " + tgt_name + "'s ship!")
                ship_cells = self.gamestate.get_ship_cells(tgt_name, row, col)
                for (r, c) in ship_cells:
                    self.gamestate.update_other_players_boards(src_name, tgt_name, row, col, 4)
                    self.draw_crash(tgt_name, r, c)
        # if we are the target
        elif self.my_name == tgt_name:
            # if src_name hit (but didn't sink) our ship, we draw a cross in our board
            if value == 2:
                self.message_label.config(text=src_name + " hit your ship!")
                self.draw_hit(tgt_name, row, col)
            # if src_name sunk our ship
            elif value == 4:
                self.message_label.config(text=src_name + " hit and sunk your ship!")
                ship_cells = self.gamestate.get_ship_cells(tgt_name, row, col)
                # we make the whole ship red in our board
                for (r, c) in ship_cells:
                    self.draw_crash(tgt_name, r, c)
                # if all our ships have now been sunk, we go into spectator mode
                if self.all_ships_sunk(tgt_name):
                    # in Gamestate, remove our name from players and add it to spectators
                    self.gamestate.remove_player(tgt_name)
                    self.gamestate.add_spectator(tgt_name)
                    # letting other players know that we are out of the game
                    self.master.notify_players("game.all_sunk", tgt_name)
                    # if we would have had to fire next, we pass the firing turn on
                    if self.gamestate.get_turn() == tgt_name:
                        self.gamestate.switch_turn()
        # if we are neither the one who fired nor the target, we only see the shot is src_name sunk one of tgt_name's ships
        else:
            if value == 4:
                self.message_label.config(text=src_name + " sunk " + tgt_name + "'s ship!")
                ship_cells = self.gamestate.get_ship_cells(tgt_name, row, col)
                # making the whole ship red in our board
                for (r, c) in ship_cells:
                    self.gamestate.update_other_players_boards(self.my_name, tgt_name, row, col, 4)
                    self.draw_crash(tgt_name, r, c)
        # updating the labels after having switched the turn
        self.switch_turn()

    # a function for cehcking whether all ships of a player have been sunk
    def all_ships_sunk(self, name):
        board = self.gamestate.get_board(name)
        for row in range(self.rows):
            for col in range(self.cols):
                # if there is at least one cell containing an unhit ship, return False
                if board[row][col] == 1:
                    return False
        return True

    # function for after receiving a message that all ships of one player have been sunk
    def rcv_all_sunk(self, name):
        # if we are the ones who just lost
        if name == self.my_name:
            self.message_label.config(text="All your ships have sunk!")
            # drawing everybody else's ship in our window (as part of going into spectator mode)
            self.draw_spectator_boards()
        # otherwise just disable that player's field so we can't fire at it any more
        else:
            self.message_label.config(text="All ships of " + name + " have sunk!")
            self.disable_field(name)
        # getting the st of all players still left in the game
        players = self.gamestate.list_players()
        # if there is only one man standing and it happens to be us
        if len(players) == 1 and self.my_name in players:
            self.gamestate.set_game_on(False)
            # we send a message that the game ended with our victory
            self.master.notify_players("game.over", self.my_name)
        # otherwise we update the labels after having switched turns
        else:
            self.switch_turn()

    # function for after receiving the "game.over" message
    def rcv_game_over(self, name):
        # make all fields disabled so they can't be fired at
        self.disable_all_fields()
        # displaying the winner's name
        if name == self.my_name:
            self.message_label.config(text="You won!")
        else:
            self.message_label.config(text=(name + " won!"))
        # an option to restart the game is made available to the leader (by making resetbutton appear)
        if self.master.leader == self.my_name:
            self.resetbutton.grid(row=3, column=0)

    # function for restarting the game
    def restart_game(self):
        # hiding the restart button
        self.resetbutton.grid_forget()
        # clearing all fields from drawn ships, missed hits and hits.
        #self.my_canvas.clear()
        #for name, canv in self.other_canvases.iteritems():
        #    canv.clear()
        # reinitializing the fields in Gamestate
        self.gamestate.restart()
        # require confirming ships again
        self.add_ship_confirm()
        # sending a message to all players that the game has restarted
        self.master.notify_players("game.restart", "")

    # function for after receiving a message that the game has restarted
    def rcv_restart_game(self):
        # clearing all fields from drawn ships, missed hits and hits.
        self.my_canvas.clear()
        for name, canv in self.other_canvases.iteritems():
            canv.clear()
        # making all fields disabled except our own (to reposition our ships)
        self.disable_all_fields()
        self.enable_field(self.my_name)
        # reenabling the "Ready"/"Start game" button
        self.startbutton.config(state="normal")
        self.message_label.config(text="Position your ships!")
        # set ship conf state to False
        self.gamestate.set_ships_confirmed(False)
        self.update_ship_label()
        # reinitialixing the set containing shipcells
        self.clear_clicks()

    # function for drawing the ships of all other players in our window after going into spectator mode
    def draw_spectator_boards(self):
        players = self.gamestate.list_players()
        for p in players:
            board = self.gamestate.get_board(p)
            for row in range(self.rows):
                for col in range(self.cols):
                    value = board[row][col]
                    # only draw unhit ships - missed hits are unnecessary and sunk ships are already visible in our window
                    if value == 1:
                        self.draw_ship(p, row, col)

    def draw_resume_boards(self):
        players = self.gamestate.list_players()
        for p in players:
            board = self.gamestate.get_board(p)
            for row in range(self.rows):
                for col in range(self.cols):
                    value = board[row][col]
                    if value == 1 and p == self.my_name:
                        self.draw_ship(p, row, col)
                    if value == 4:
                        self.draw_crash(p,row,col)

    # marking ourselves as ready to start the game, after having positioned our ships - apllies to everybody but the leader
    def ready(self):
        # if all our ships have been positioned correctly
        if self.validate_ships():
            # save our state in Gamestate as "ready"
            self.gamestate.set_ready(self.my_name)
            self.message_label.config(text="You're ready.")
            # getting all our ships and saving them in Gamestate
            ships = self.get_clicks(self.my_name)
            self.gamestate.add_board(self.my_name, ships)
            # disabling all fields, including ours (so we can't change the position of our ships)
            self.disable_all_fields()
            self.disable_field(self.my_name)
            # makind the "Ready" button disabled
            self.startbutton.config(state="disabled")
            # notifying everybody that we are ready
            self.master.notify_players('game.ready',self.my_name)
        else:
            self.message_label.config(text="Ship validation failed.")

    # function that returns whether a ship sinks
    def ship_shinks(self, tgt_name, ship_cells):
        board = self.gamestate.get_board(tgt_name)
        # if all the cells in that ship have been marked as "hit", it sinks
        return all(board[r][c] == 2 for (r, c) in ship_cells)

    # updating the message_label after having switched turns
    def switch_turn(self):
        turn = self.gamestate.get_turn()
        self.master.colour_turn(turn)
        if "Waiting" in self.message_label.cget("text"):
            s = ""
        else:
            s = self.message_label.cget("text") + "\n"
        print "Here, I am", self.my_name, "it's ", turn, "'s turn."
        # if it's our turn to fire, we display such message and enable all other players' fields for us to fire
        if turn == self.my_name:
            self.message_label.config(text=(s + "Your turn!"))
            for p in self.gamestate.list_players():
                self.enable_field(p)
            self.disable_field(self.my_name)
        # if it's somebody else's turn to fire, we disable all fields (in case we were the previous one)
        else:
            self.message_label.config(text=(s + "Waiting for " + turn + "."))
            self.disable_all_fields()

    # changing the "Ready" button into a "Start game" button after gaining leadership after the previous leader left
    def add_leader_button(self):
        self.startbutton.config(text='Start game', command=self.start_game)
        if not self.gamestate.get_game_on():
            self.startbutton.config(state="normal")
        self.kick_entry = tk.Entry(self.button_frame)
        self.kick_entry.grid(row=5,column=0)
        self.kick_button = tk.Button(self.button_frame, text='Kick disconnected player', command=self.kick)
        self.kick_button.grid(row=6, column=0)


    def kick(self):
        player_name = self.kick_entry.get()
        self.master.notify_players('game.kick',player_name)

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

    # drawing a shipcell in our window on a given person's board
    def draw_ship(self, name, row, col):
        if name == self.my_name:
            self.my_canvas.draw_ship(row, col)
        elif name in self.other_canvases:
            self.other_canvases[name].draw_ship(row, col)
        else:
            Log.debug('Do not have player %s' % name)

    # drawing a missed hit cell in our window on a given person's board
    def draw_miss(self, name, row, col):
        if name == self.my_name:
            self.my_canvas.draw_miss(row, col)
        elif name in self.other_canvases:
            self.other_canvases[name].draw_miss(row, col)
        else:
            Log.debug('Do not have player %s' % name)

    # drawing a hit ship cell in our window on a given person's board
    def draw_hit(self, name, row, col):
        if name == self.my_name:
            self.my_canvas.draw_hit(row, col)
        elif name in self.other_canvases:
            self.other_canvases[name].draw_hit(row, col)
        else:
            Log.debug('Do not have player %s' % name)

    # drawing a sunk ship cell in our window on a given person's board
    def draw_crash(self, name, row, col):
        print "CRASH"
        if name == self.my_name:
            self.my_canvas.draw_crash(row, col)
        elif name in self.other_canvases:
            self.other_canvases[name].draw_crash(row, col)
        else:
            Log.debug('Do not have player %s' % name)

    # enabling a given person's field for us to fire (click) at
    def enable_field(self, name):
        if name == self.my_name:
            self.my_canvas.enable_input()
        elif name in self.other_canvases:
            self.other_canvases[name].enable_input()
        else:
            Log.debug('Do not have player %s' % name)

    # disabling a given person's field to prevent us from firing (clicking) there
    def disable_field(self, name):
        if name == self.my_name:
            self.my_canvas.disable_input()
        elif name in self.other_canvases:
            self.other_canvases[name].disable_input()
        else:
            Log.debug('Do not have player %s' % name)

    # enabling all fields for us to click at
    def enable_all_fields(self):
        for name in self.other_canvases:
            self.enable_field(name)

    # disabling all fields to prevent us from clicking there
    def disable_all_fields(self):
        for name in self.other_canvases:
            self.disable_field(name)

    # storing the location of the last click we made (on whose board, in which row and column)
    def set_last_click(self, name, row, col):
        self.last_click_loc = name, row, col
        # if we haven't clicked there yet
        if self.last_click_loc not in self.clicks_set:
            # we add that location to the set of clicks
            self.clicks_set.add(self.last_click_loc)
            # if it's our own board, we draw a ship there
            if name == self.my_name:
                self.my_canvas.draw_rec(row, col, SHIP_COL)
        # otherwise we remove that location from the set of clicks
        else:
            self.clicks_set.remove(self.last_click_loc)
            # if it's our own board, we repaint repaint the cell with sea
            if name == self.my_name:
                self.my_canvas.draw_rec(row, col, SEA_COL)

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
        return validate_ships(ships, self.rows, self.cols, self.gamestate.get_req_ships())

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
                else:
                    self.draw_rec(row, col, SEA_COL)

    def draw_ship(self, row, col):
        self.draw_rec(row, col, SHIP_COL)

    def draw_miss(self, row, col):
        self.draw_x(row, col)

    def draw_hit(self, row, col):
        self.draw_rec(row, col, SHIP_COL)
        self.draw_x(row, col)

    def draw_crash(self, row, col):
        self.draw_rec(row, col, CRASH_COL)
        self.draw_x(row, col)

    def draw_rec(self, row, col, color):
        x0 = (col+1) * self.box_edge
        y0 = (row+1) * self.box_edge
        self.create_rectangle((x0, y0, x0+self.box_edge, y0+self.box_edge), fill=color)

    def draw_x(self, row, col):
        x0 = (col+1) * self.box_edge
        y0 = (row+1) * self.box_edge
        self.create_line(x0, y0, x0+self.box_edge, y0+self.box_edge)
        self.create_line(x0, y0+self.box_edge, x0+self.box_edge, y0)

    def enable_input(self):
        # bind mouseclick
        self.bind("<Button-1>", self.canvas_mouseclick)
        self.draw_rec(-1, -1, 'green')

    def disable_input(self):
        self.unbind("<Button-1>")
        self.draw_rec(-1, -1, 'red')

    # function for handling a mousclick on the canvas
    def canvas_mouseclick(self, event):
        x, y = event.x, event.y
        # getting the location of the click
        row = int(y / self.box_edge - 1)
        col = int(x / self.box_edge - 1)
        if row < self.rows and row >= 0 and col < self.cols and col >= 0:               # creating ships only within bounds
            self.root.set_last_click(self.name, row, col)
        print str(self.name) + ": " + '%d %d' % (row, col)
        # if we clicked on somebody else's board, we check if we can fire there
        if self.master.my_name != self.name and row < self.rows and col < self.cols:    # firing only within the bounds of other players' boards
            tgt_board = self.root.gamestate.get_other_players_boards()[self.master.my_name][self.name]
            cell_value = tgt_board[row][col]
            # getting the cell value of the click we made - if it's 0 (empty) or 1 (unhit shipcell), we fire there
            if cell_value < 2:      # if it's 2 (hit by us), 3 (missed by us) or 4 (crashed by anyone), we can't fire there any more
                self.master.fire(self.master.my_name, self.name, row, col)

    def clear(self):
        for row in range(self.rows):
            for col in range(self.cols):
                self.draw_rec(row, col, SEA_COL)


if __name__ == '__main__':
    my_game = [[0 for _ in range(10)] for _ in range(10)]
    other_games = {str(i):[[randint(0, 5) for _ in range(10)] for _ in range(10)] for i in range(2)}

    root = tk.Tk()
    root.title("Blah blah")
    mainframe = Gamebox(root, 'myself', my_game, other_games)
    mainframe.grid(sticky=(tk.N, tk.W, tk.E, tk.S))

    root.mainloop()
