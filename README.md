# meowtop 

task manager but with a cat who really hates you

meowtop is a system monitor i made in python because checking my ram usage wasn't enough. now there's a cat who judges me for it too.

his name is tuft. he's not very nice.

## features

- live cpu, ram, and disk usage
- running process list with searching and sorting
- configurable ram usage warnings
- windows notifications when your ram gets too high
- notification history
- tuft, who reacts to whatever your computer is doing
- animated tuft sprites with different moods
- you can pet him (he likes that)
- he falls asleep when he's bored
- a button specifically for making him insult your computer

## downloads

check the [releases](../../releases) tab for the latest version.

currently windows only.

if you don't trust random executables from github (fair enough), you can look through the source code or run it yourself.

## running from source

you'll need python 3.10+ and these libraries:

```bash
pip install PyQt6 psutil
```

download the source files, make sure `tuft-sprites.png` is in the same folder as `main.py`, then run:

```bash
python main.py
```

## why did i make this

i was checking task manager and realized how many resources my computer was using.

so naturally, instead of fixing that problem, i decided to make another program that uses more resources.

now i can watch my ram usage while a purple cat insults me.

very productive.

## notes

- this isn't supposed to completely replace windows task manager
- some system processes might not be accessible without administrator permissions
- the disk percentage shows storage space used, not disk activity
- tuft's opinions do not reflect those of the developer (usually)

made with python, pyqt6, and psutil.

meow.
