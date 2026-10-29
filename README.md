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

## running meowtop


currently windows only. no exe download for now because windows defender thinks my cat is a trojan.

you'll need python installed.

```bash
pip install -r requirements.txt
python main.py
```

make sure `tuft-sprites.png` is in the same folder as `main.py`.

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

<img width="1918" height="1076" alt="Screenshot 2026-10-29 163635" src="https://github.com/user-attachments/assets/787bcca6-e8ec-475b-95a1-297b9d75e8a1" />
<img width="1078" height="764" alt="image" src="https://github.com/user-attachments/assets/1d79c692-9c58-4d21-9f2b-89099c7a61e8" />


made with python, pyqt6, and psutil.

meow.
