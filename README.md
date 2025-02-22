# **Typ-Wars**
## A simple SP and LAN MP typing game
### How to play
Type the words on spawning on screen to destroy them before they reach the bottom of the screen.
In multiplayer mode you can also type dictionary words to send them to your opponent.
### Lives
You have 3 lives, you lose a life if a word reaches the bottom of the screen.
### Scoring
Score system which increases difficulty with your score.
### Difficulty
Difficulty comes from faster falling speed, longer words and more words on screen at the same time.
There are 6 difficulty levels.
### Multiplayer
LAN P2P multiplayer feature with peer discovery done via local multicast.
Lobby chat available before starting multiplayer game.
Ready system for client to let the server know that they are ready to start the game.
P2P network communication through sockets and listener threads.
Multiplayer has word spawner with reduced frequency.
Players mostly try to send each other words to compete.
If you send a word which is already on your opponent's screen, you will help them out!
### Potential improvements (no guarantees)
Adding scrollbar for text chat.
Adding sounds.
Adding music.
Adding highlighter for when you have partially typed a word on screen.
Coloring words sent by generator vs your opponent to differentiate them.
