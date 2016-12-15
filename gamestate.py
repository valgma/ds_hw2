import Pyro4

@Pyro4.expose
class GameState(object):
    def __init__(self, board_size):
        self.players = set()
        self.board_size = board_size
        self.boards = {}
        self.other_players_boards = {}
        self.ready_players = set()
        self.turn = ""
        self.turns = []
        self.game_on = False
        self.spectators = set()
        self.req_ships = {2:None, 3:None, 4:None, 5:None}
        self.ships_confirmed = False

    # function returning the set of all players still in the game
    def list_players(self):
        return self.players

    # adding a player to the set of players
    def add_player(self, name):
        self.players.add(name)

    # removing a player from all possible fields
    def remove_player(self, name):
        if name in self.players:
            self.players.remove(name)
        if name in self.ready_players:
            self.ready_players.remove(name)
        if self.turn == name:   #TODO: check if it's necessary or already covered
            self.switch_turn()
        if name in self.turns:
            self.turns.remove(name)

    # function returning the board size
    def get_board_size(self):
        return self.board_size

    # function returning the dictionary of boards of all players
    def get_boards(self):
        return self.boards

    # function for returning the board of a certain player
    def get_board(self, name):
        return self.boards[name]

    # restarting the game and reinitializing all necessary fields
    def restart(self):
        self.players = self.players.union(self.spectators)
        self.spectators = set()
        self.ready_players = set()
        self.boards = {}
        self.other_players_boards = {}
        self.req_ships = {2:None, 3:None, 4:None, 5:None}

    # function returning the boards of all players as viewed by all players (dictionary of dictionaries).
    def get_other_players_boards(self):
        return self.other_players_boards

    # function returning whether the game is currently running
    def get_game_on(self):
        return self.game_on

    # setting the game on or off
    def set_game_on(self, value):
        self.game_on = value

    def testmethod(self):
        return "this method tests if you can get stuff from uri fine.".split()

    # marking a player as ready
    def set_ready(self, name):
        self.ready_players.add(name)

    # returning whose turn it is to fire
    def get_turn(self):
        return self.turn

    # switching the turn
    def switch_turn(self):
        self.turns.append(self.turn)
        self.turn = self.turns[0]
        self.turns.pop(0)

    # a function returning whether a certain player is ready
    def is_ready(self, name):
        return name in self.ready_players

    # getting the number of ready players
    def get_ready_players_count(self):
        return len(self.ready_players)

    # creating an order of turns
    def init_turns(self, name):
        self.turn = name
        self.turns = list(self.list_players())
        self.turns.remove(name)

    # updating a cell value in a certain person's board
    def update_boards(self, name, row, col, value):
        self.boards[name][row][col] = value

    # updating a cell value in a certain person's board, as viewed by all other players
    def update_other_players_boards(self, src_name, tgt_name, row, col, value):
        self.other_players_boards[src_name][tgt_name][row][col] = value

    # creating a board with given ship locations
    def add_board(self, name, ships):
        board = [[0 for i in range(self.board_size)] for j in range(self.board_size)] # empty board
        for (row, column) in ships:
            board[row][column] = 1
        self.boards[name] = board

    # creatig other players boards
    def add_other_players_boards(self):
        for player in self.ready_players:
            other_players_boards = {}
            for other_player in self.players:
                if player != other_player:
                    other_players_boards[other_player] = [[0 for i in range(self.board_size)] for j in range(self.board_size)] # empty board
            self.other_players_boards[player] = other_players_boards

    # funtion for getting all the cells of the corresponding ship by one given cell
    def get_ship_cells(self, name, row, column):
        board = self.boards[name]
        ship_cells = set()
        for i in range(row, -1, -1):
            if self.is_ship(board[i][column]):
                ship_cells.add((i, column))
            else:
                break
        for i in range(row, self.board_size):
            if self.is_ship(board[i][column]):
                ship_cells.add((i, column))
            else:
                break
        for i in range(column, -1, -1):
            if self.is_ship(board[row][i]):
                ship_cells.add((row, i))
            else:
                break
        for i in range(column, self.board_size):
            if self.is_ship(board[row][i]):
                ship_cells.add((row, i))
            else:
                break
        return ship_cells

    # function returning whether a cell holds a ship (unhit, hit or sunk) or not
    def is_ship(self, cell_value):
        return cell_value == 1 or cell_value == 2 or cell_value == 4

    # function returning whether a certain person is a spectator
    def is_spectator(self, name):
        return name in self.spectators

    # adding a spectator
    def add_spectator(self, name):
        self.spectators.add(name)

    # function returning whether the leader has confirmed the ships or not
    def are_ships_confirmed(self):
        return self.ships_confirmed

    # adding the numbers for ships per length
    def add_req_ships(self, ship2, ship3, ship4, ship5):
        self.req_ships = {2:ship2, 3:ship3, 4:ship4, 5:ship5}
        self.ships_confirmed = True

    # getting the numbers for ships per length
    def get_req_ships(self):
        return self.req_ships

    # returning the number of ships for a given length
    def get_ship_count(self, nr):
        try:
            return self.req_ships[nr]
        except Exception as e:
            print "Illegal ship length:", str(nr)
            return
