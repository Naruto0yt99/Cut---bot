import random

WORDS=["anime","naruto","kakashi","onepiece","ramen","mahadev","uttarakhand"]
CHARACTERS=["Naruto","Kakashi","Luffy","Gojo","Tanjiro","Levi","Hinata"]

def new_word_game():
    return random.choice(WORDS)

def new_character_game():
    return random.choice(CHARACTERS)
