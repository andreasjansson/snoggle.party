from snoggle.abstract_player import AbstractPlayer


class HumanPlayer(AbstractPlayer):

    def __init__(self, color):
        super(HumanPlayer, self).__init__(color)
        self.sid = None
        self.is_bot = False
