import Pyro4

@Pyro4.expose
class GameState(object):
    def __init__(self):
        self.players = []

    def list_players(self):
        return self.players

    def testmethod(self):
        return "this method tests if you can get stuff from uri fine.".split()
