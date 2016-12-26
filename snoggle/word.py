from snoggle import dictionary

class Word(object):

    def __init__(self, player, cells=None):
        self.player = player
        self.cells = cells or []
        self.previous_owner_colors = set()

    def letters(self):
        return ''.join([c.letter.lower() for c in self.cells])

    def positions(self):
        return [(c.position) for c in self.cells]

    def score(self):
        assert self.is_in_dictionary()
        return sum([dictionary.SCORES[c.lower()] for c in self.letters()])

    def is_in_dictionary(self):
        return self.letters().lower() in dictionary.WORDS

    def append(self, cell):
        self.cells.append(cell)

    def contains(self, cell):
        return cell in self.cells

    def is_equivalent(self, other):
        self_positions = [c.position for c in self.cells]
        other_positions = [c.position for c in other.cells]
        return (frozenset(self_positions) == frozenset(other_positions)
                and self.letters() == other.letters())

    def __len__(self):
        return len(self.cells)

    def steal(self, new_player):
        self.previous_owner_colors.add(self.player.color)
        self.player = new_player
        for cell in self.cells:
            new_player.seen_positions.add(cell.position)


def score_words(words):
    return sum([w.score() for w in words])
