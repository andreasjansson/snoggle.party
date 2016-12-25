import os

SCORES = {
    'a': 1,
    'b': 3,
    'c': 3,
    'd': 2,
    'e': 1,
    'f': 4,
    'g': 2,
    'h': 4,
    'i': 1,
    'j': 8,
    'k': 5,
    'l': 1,
    'm': 3,
    'n': 1,
    'o': 1,
    'p': 3,
    'q': 9, # 10 - 1 (q is always qu. q is 10, u is 1, but both counted here)
    'r': 1,
    's': 1,
    't': 1,
    'u': 1,
    'v': 4,
    'w': 4,
    'x': 8,
    'y': 4,
    'z': 10,
}


def read_words():
    cwd = os.path.dirname(os.path.abspath(__file__))
    words = set()
    with open(os.path.join(cwd, 'words.csv')) as f:
        for line in f:
            words.add(line.strip().lower())

    return words


WORDS = read_words()


def contains(word):
    return word.letters().lower() in WORDS


def score(word):
    return sum([SCORES[c.lower()] for c in word.letters()])
