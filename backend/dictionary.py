import os

SCORES = {
    'a': 1,
    'e': 1,
    'i': 1,
    'o': 1,
    'u': 1,
    'l': 1,
    'n': 1,
    'r': 1,
    's': 1,
    't': 1,
    'd': 2,
    'g': 2,
    'b': 3,
    'c': 3,
    'm': 3,
    'p': 3,
    'f': 4,
    'h': 4,
    'v': 4,
    'w': 4,
    'y': 4,
    'k': 5,
    'j': 8,
    'x': 8,
    'q': 9, # 10 - 1 (q is always qu, q is 10 and u is 1 but both counted here)
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
