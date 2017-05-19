#!/usr/bin/python3

import midi, re
from decimal import Decimal

"""
Looking at the Vienna 4x22 data, these are the relevant item names:

Solo items: info meta
Left side: insertion snote
Right Side: deletion no_played_note note

So no ornament, hammer_bounce, trill, trailing_played_note, no_score_note, no_played_note or trailing_score_note.
Therefore I gnore these for now.
You can see for yourself by invoking these commands in data/match folder.
cat *match | sed 's/(.*//g' | sort -u
cat *match | sed 's/.*)-//g' | sed 's/(.*//g' | sort -u

The documentation of Match File Format is terrible. It doesn't contain important information
and what is more it is a documentation of the version 3.0 of the format. The dataset itself
uses version 5.0 and an unknown version (likely older than 3.0).
"""

DEFAULT_VELOCITY = 64

def parse_params(params):
    if params is None:
        return []
    params = params[1:-1] # remove ( and )
    found = re.findall(r"\[[^]]*\]|[^,[]+", params)
    result = []
    for r in found:
        if len(r) > 0 and r[0] == '[':
            result.append(r[1:-1].split(","))
        else:
            result.append(r)
    return result

def parse_line(line):
    match_duo = re.match(r"([a-z_]*)(\(.*\))?\-([a-z_]*)(\(.*\))?\.", line)
    if match_duo is not None:
        left_name, left_params, right_name, right_params = match_duo.groups()
        return ((left_name, parse_params(left_params)), (right_name, parse_params(right_params)))
    match_solo = re.match(r"([a-z_]*)(\(.*\))?\.", line)
    if match_solo is not None:
        name, params = match_solo.groups()
        return ((name, parse_params(params)),)
    return None

class Note:
    NOTES = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b', 'b#']

    def __init__(self, parsed_line, is_old):
        name, data = parsed_line
        self.is_old = is_old
        if name == 'snote':
            self.is_score = True
            anchor, note_info, octave, bar_beat, offset, duration, beat_number, beat_duration, attr_list = data
            self.anchor = anchor
            self.note = note_info[0].lower()
            if note_info[1] == '#':
                self.is_sharp = True
                self.note += '#'
            elif note_info[1] == 'n':
                self.is_sharp = False
            elif note_info[1] == 'b':
                self.is_sharp = True
                self.note = Note.NOTES[Note.NOTES.index(self.note) - 1]
            else: raise ValueError("Unknown snote modifier {}.".format(note_info[1]))
            self.octave = int(octave)
            self.bar, self.beat = map(int, bar_beat.split(':'))
            self.offset = offset #?
            self.duration = duration #?
            self.time_onset = Decimal(beat_number)
            self.time_offset = Decimal(beat_duration)
            # beat_duration isn't actually duration in beats but documentation of the format is terrible
            # and calls this attribute DurationInBeats.
            self.attributes = attr_list
        elif name == 'note':
            self.is_score = False
            try:
                anchor, note_info, octave, onset, offset, adj_offset, velocity = data
            except ValueError:
                anchor, note_info, octave, onset, offset, velocity = data
                adj_offset = offset
            assert(adj_offset == offset) # ?
            self.anchor = int(anchor)
            self.note = note_info[0].lower()
            if note_info[1] == '#':
                self.is_sharp = True
                self.note += '#'
            elif note_info[1] == 'n':
                self.is_sharp = False
            elif note_info[1] == 'b':
                self.is_sharp = True
                self.note = Note.NOTES[Note.NOTES.index(self.note) - 1]
            else: raise ValueError("Unknown note modifier {}.".format(note_info[1]))
            self.octave = int(octave)
            self.time_onset = Decimal(onset)
            self.time_offset = Decimal(offset)
            self.velocity = velocity
        else:
            raise ValueError("Invalid note line: {}".format(parsed_line))

    @property
    def midi_note_number(self):
        starts_from_one = 0 if self.is_old else 1
        return 12 * (self.octave + starts_from_one) + Note.NOTES.index(self.note)

    def get_event(self, is_off):
        velocity = int(self.velocity) if hasattr(self, 'velocity') else DEFAULT_VELOCITY
        time = self.time_offset if is_off else self.time_onset
        if velocity < 0:
            velocity = 0 
            # There is negative velocity in the match files, no idea why.
            # That particular note has no corresponding note in the midi files.
        return (time, is_off, self.midi_note_number, velocity)

    @property
    def on_event(self):
        return self.get_event(False)

    @property
    def off_event(self):
        return self.get_event(True)

    def __str__(self):
        result = []
        if self.is_score: result.append("score")
        else: result.append("played")
        result.append(self.note + ('#' if self.is_sharp else ''))
        result.append(str(self.octave))
        result.append(str(self.time_onset))
        result.append(str(self.time_offset))
        if self.is_score:
            result.append(str(self.bar))
            result.append(str(self.beat))
            result.append(self.duration)
            result.append(self.offset)
        result.append(str(self.midi_note_number))
        return ' '.join(result)


    @staticmethod
    def from_parsed(parsed_note, is_old):
        if parsed_note[0] in ('insertion', 'deletion', 'no_played_note'):
            return None
        return Note(parsed_note, is_old)

class MatchFile:
    def __init__(self, match_file):
        if isinstance(match_file, str):
            match_file = open(match_file)
        self.info = {}
        self.meta = {}
        self.matches = []
        for line in match_file:
            parsed = parse_line(line)
            if parsed is None:
                raise ValueError("Invalid file format: {}".format(line))
            if len(parsed) == 1:
                data_name, data = parsed[0]
                if data_name == 'info':
                    self.info[data[0]] = data[1]
                elif data_name == 'meta': # possible collisions with info
                    self.meta[data[0]] = data[1:]
                else:
                    pass # ?
            elif len(parsed) == 2:
                is_old = not 'matchFileVersion' in self.info
                self.matches.append((
                    Note.from_parsed(parsed[0], is_old), 
                    Note.from_parsed(parsed[1], is_old)))

    @property
    def score_notes(self):
        for score_note, _ in self.matches:
            if score_note is not None:
                yield score_note

    @property
    def played_notes(self):
        for _, played_note in self.matches:
            if played_note is not None:
                yield played_note
                
    def get_pattern(self, time_scaling=Decimal(1.0), score_notes=True):
        events = []
        for note in self.score_notes if score_notes else self.played_notes:
            events.append(note.on_event)
            events.append(note.off_event)
        events = sorted(events)

        time_scalind = 10000
        current_time = None
        track = midi.Track()
        #track.append(midi.SetTempoEvent(tick=0, data=[7, 161, 32]))
        for time, is_off, note_number, vel in events:
            if current_time is None:
                current_time = time
            tick = int((time - current_time) * time_scaling)
            if is_off:
                track.append(midi.NoteOffEvent(tick=tick, pitch=note_number, velocity=64))
            else:
                track.append(midi.NoteOnEvent(tick=tick, pitch=note_number, velocity=vel))
            current_time = time

        track.append(midi.EndOfTrackEvent(tick=1))
        pattern = midi.Pattern()
        pattern.resolution = int(self.info['midiClockUnits']) 
        pattern.append(track)
        return pattern

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description='Converts .match file to .mid file.')
    parser.add_argument('input_file', type=str,
                        help='input .match file')
    parser.add_argument('output_file', type=str,
                        help='output .mid file')
    parser.add_argument('--notes', '-n', dest='notes',
                        default='score', choices=['score', 'played'],
                        help='"score" or "played" - which notes you want to convert, score is default')
    parser.add_argument('--scaling', '-s', dest='scaling',
                        default="1.0", type=str,
                        help='time scaling of events in the .mid file')
    parser.add_argument('--debug', '-d', action='store_const',
                        default = False, const = True,
                        help='prints debug information')

    args = parser.parse_args()
    score_notes = args.notes == 'score'
    match_file = MatchFile(args.input_file)
    pattern = match_file.get_pattern(time_scaling=Decimal(args.scaling), score_notes=score_notes)
    if args.debug:
        print(pattern)
    midi.write_midifile(args.output_file, pattern)

