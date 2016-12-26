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

def read_common_words(known_words):
    cwd = os.path.dirname(os.path.abspath(__file__))
    words = []
    with open(os.path.join(cwd, 'common_words.tsv')) as f:
        for line in f:
            word = line.split('\t')[0].lower()
            if word in known_words:
                words.append(word)

    return words


WORDS = read_words()
COMMON_WORDS = read_common_words(WORDS)
