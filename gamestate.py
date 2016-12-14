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

    def list_players(self):
        return self.players

    def add_player(self, name):
        self.players.add(name)

    def remove_player(self, name):
        if name in self.players:
            self.players.remove(name)
        if self.turn == name:   #TODO: check if it's necessary or already covered
            self.switch_turn()
        if name in self.turns:
            self.turns.remove(name)

    def get_board_size(self):
        return self.board_size

    def get_boards(self):               #returns the dictionary of all boards
        return self.boards

    def get_board(self, name):          #returns the board of a certain player
        return self.boards[name]

    def get_boards(self):
        return self.boards

    def restart(self):
        self.players = set()
        self.spectators = set()
        self.turns = []
        self.boards = {}
        self.other_players_boards = {}

    def get_other_players_boards(self):
        return self.other_players_boards

    def get_game_on(self):
        return self.game_on

    def set_game_on(self, value):
        self.game_on = value

    def testmethod(self):
        return "this method tests if you can get stuff from uri fine.".split()

    def set_ready(self, name):
        self.ready_players.add(name)

    def get_turn(self):
        return self.turn

    def switch_turn(self):
        self.turns.append(self.turn)
        self.turn = self.turns[0]
        self.turns.pop(0)

    def is_ready(self, name):
        return name in self.ready_players

    def get_ready_players_count(self):
        return len(self.ready_players)

    def init_turns(self, name):
        self.turn = name
        self.turns = list(self.list_players())
        self.turns.remove(name)

    def update_boards(self, name, row, col, value):
        self.boards[name][row][col] = value

    def update_other_players_boards(self, src_name, tgt_name, row, col, value):
        self.other_players_boards[src_name][tgt_name][row][col] = value

    def add_board(self, name, ships):
        board = [[0 for i in range(self.board_size)] for j in range(self.board_size)] # empty board
        for (row, column) in ships:
            board[row][column] = 1
        self.boards[name] = board

    def add_other_players_boards(self):
        for player in self.ready_players:
            other_players_boards = {}
            for other_player in self.players:
                if player != other_player:
                    other_players_boards[other_player] = [[0 for i in range(self.board_size)] for j in range(self.board_size)] # empty board
            self.other_players_boards[player] = other_players_boards

    def get_ship_cells(self, name, row, column):        # funtion for getting all the cells of the corresponding ship by one given cell
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

    def is_ship(self, cell_value):
        return cell_value == 1 or cell_value == 2 or cell_value == 4

    def is_spectator(self, name):
        return name in self.spectators

    def add_spectator(self, name):
        self.spectators.add(name)