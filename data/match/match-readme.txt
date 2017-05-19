Match File Format (version 3.0)

(by Gerhard Widmer, Emilios Cambouropoulos, Simon Dixon, 1998, 2004 2005, http://www.ofai.at/music/, development of file format supported by the Austrian Science Fund, Y99-INF)

for matched score + performance (MIDI) files
--------------------------------------------

Each line in a match file is of one of the following forms:
	hammer_bounce-PlayedNote.
	info(Attribute, Value).
	insertion-PlayedNote.
	ornament(Anchor)-PlayedNote.
	ScoreNote-deletion.
	ScoreNote-PlayedNote.
	ScoreNote-trailing_score_note.
	trailing_played_note-PlayedNote.
	trill(Anchor)-PlayedNote.

ScoreNote is of the form:
	snote(Anchor,[NoteName,Modifier],Octave,Bar:Beat,Offset,Duration,
			BeatNumber,DurationInBeats,ScoreAttributesList)
	e.g. snote(n1,[b,b],5,1:1,0,3/16,0,0.75,[s])

PlayedNote is of the form:
	note(Number,[NoteName,Modifier],Octave,Onset,Offset,AdjOffset,Velocity)
	e.g. note(1,[a,#],5,5054,6362,6768,53)

HEADER INFOS:

info(matchFileVersion,2.0).
info(scoreFileName,'kv281_1_1.scr').
info(midiFileName,'kv281_1_1_a.mid').
info(midiClockUnits,480).
info(midiClockRate,500000).
info(keySignature,[bb,major]).
info(timeSignature,2/4).
info(beatSubdivision,[2,4,8]).
info(tempoIndication,[allegro]).
info(approximateTempo,70).
info(subtitle,[]).

additional header infos (from version 3.0 onwards):
	audio file name
	audio first note: the time of the first note in the audio file, in seconds
	path names for all files (score, midi, audio)
	composer
	performer


SCORE NOTE - PLAYED NOTE PAIRS:

snote(n1,[b,b],5,1:1,0,3/16,0,0.75,[s,trill])-note(1,[a,#],5,1213,1440,2140,56).

(where the arguments of 'note' are
- number
- pitch name
- octave
- note onset
- note (key) offset ("key off")
- note (sound) offset ("sound off") = max(keyoff,pedaloff)
- velocity)

ANNOTATION OF MISSING/EXTRA NOTES:

trailing_played_note-note(_,_,_,_,_,_,_).
       hammer_bounce-note(_,_,_,_,_,_,_).
     trill(AnchorId)-note(_,_,_,_,_,_,_).
  ornament(AnchorId)-note(_,_,_,_,_,_,_).
           insertion-note(_,_,_,_,_,_,_).

snote(_,_,_,_,_,_,_,_,_)-trailing_score_note.
snote(_,_,_,_,_,_,_,_,_)-deletion.

and for compatibility with old match files:

no_score_note-note(_,_,_,_,_,_,_).
snote(_,_,_,_,_,_,_,_,_)-no_played_note.


ATTRIBUTES OF NOTES:
(as recognised by beatroot; see event.h eventMidi.cpp)

adlib	ADLIB_FLAG
arp		ARPEGGIO_FLAG
double	DOUBLE_FLAG			// grace notes: up main up
fermata	FERMATA_FLAG
grace	GRACE_NOTE_FLAG
le		LEGATO_END_FLAG
ls		LEGATO_START_FLAG
m		MIDDLE_FLAG
mord	MORDENT_FLAG		// main up main down; or v/v
s		MELODY_FLAG
stacc	STACCATO_FLAG
trill	TRILL_FLAG			// upper or main note start

#define ADLIB_FLAG             0x1
#define ARPEGGIO_FLAG          0x2
#define DOUBLE_FLAG            0x4
#define FERMATA_FLAG           0x8
#define GRACE_NOTE_FLAG       0x10
#define MELODY_FLAG           0x20
#define MIDDLE_FLAG           0x40
#define MORDENT_FLAG          0x80
#define ORNAMENT_FLAG        0x100
#define STACCATO_FLAG        0x200
#define TRILL_FLAG           0x400
#define UNSCORED_FLAG        0x800
#define LEGATO_START_FLAG   0x1000
#define LEGATO_END_FLAG     0x2000

