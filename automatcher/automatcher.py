#!/usr/bin/python3

import midi
from itertools import zip_longest, chain
from functools import lru_cache
from enum import Enum
from copy import copy, deepcopy

INF = float("inf")

interesting_event_types = (midi.NoteOnEvent, midi.NoteOffEvent)
def default_event_filter(event):
    return type(event) in interesting_event_types

def default_event_comparer(a, b):
    if a is None or b is None:
        return False
    if type(a) != type(b):
        return False
    return a.data[0] == b.data[0]

class Event:
    def __init__(self, midi_event, pos, time):
        self.midi_event = midi_event
        self.pos = pos
        self.time = time
        self.symbol = None

    event_type_names = {
        midi.ControlChangeEvent : "CCE",
        midi.SetTempoEvent : "STe",
        midi.NoteOnEvent : "On",
        midi.NoteOffEvent : "Off",
        midi.EndOfTrackEvent : "EOT"
    }

    SHOW_TIME = True
    LONG_SYMBOL = True
    TEMPLATE = "{0:>4} {2:>3} {3:>3} "
    if SHOW_TIME:
        TEMPLATE = "{0:>4} {1:>8} {2:<3} {3:>3} "
    if LONG_SYMBOL:
        TEMPLATE += "{4:<5}"
    else:
        TEMPLATE += "{4:<1}"
    TEMPLATE += " |"

    def __str__(self):
        typestr = Event.event_type_names.get(type(self.midi_event), "UNK")
        data = ""
        if type(self.midi_event) in (midi.NoteOnEvent, midi.NoteOffEvent):
            data = self.midi_event.data[0]
        symbol = self.symbol if self.symbol else ""
        return Event.TEMPLATE.format(self.pos, self.time, typestr, data, symbol)

    def is_similar(self, other): 
        if other is None:
            return False
        return default_event_comparer(self.midi_event, other.midi_event)


def preprocess(track):
    
    track = filter(default_event_filter, track) # Remove unwanted events
    result = []
    time = 0
    for i, event in enumerate(track):
        time += event.tick
        result.append(Event(event, i, time))
    return result

def group_events(track):
    result = []
    current_group = []
    for event in track:
        if event.midi_event.tick == 0:
            current_group.append(event)
        else:
            if current_group:
                result.append(current_group)
            current_group = [event]
    if current_group:
        result.append(current_group)
    return result

class TrackIterator:
    def __init__(self, data):
        self.iterator = iter(data)
        self.unmatched = []
        self.iter_pos = 0
        self.time = 0
        self.peeked = None

    def get_next(self):
        event = self.peeked 
        self.peeked = None
        if event is None:
            event = next(self.iterator)
        self.time = event.time
        self.iter_pos += 1
        return event

    def peek_next(self):
        if self.peeked is not None:
            return self.peeked
        self.peeked = next(self.iterator)
        return self.peeked

    # Finds the next event and all events that match it's time.
    def get_next_events(self):
        result = [self.get_next()]
        try:
            while self.peek_next().midi_event.tick == 0: # if takes 0 time
                result.append(self.get_next())
        except StopIteration:
            pass # return what we already found, next get_next_events will fail from get_next() on the first line
        return result

    def find_matching(self, target_events, max_gap_size=None, max_unmatched=None):
        results = [None for target in target_events]

        if max_unmatched is not None:
            self.unmatched = self.unmatched[-max_unmatched:]

        for i, event in enumerate(self.unmatched):
            for j, target_event in enumerate(target_events):
                if event.is_similar(target_event) and results[j] is None:
                    self.unmatched[i] = None
                    event = copy(event)
                    event.symbol = "!"
                    results[j] = event
                    break
        # clean up unmatched (no deletion during iteration)
        self.unmatched = [x for x in self.unmatched if x is not None]

        maybe_unmatched = []
        while (max_gap_size is None or len(maybe_unmatched) <= max_gap_size) and not all(results):
            try:
                event = self.get_next()
            except StopIteration:
                break
            for j, target_event in enumerate(target_events):
                if event.is_similar(target_event) and results[j] is None:
                    # store unmatched
                    self.unmatched += maybe_unmatched
                    maybe_unmatched = []
                    results[j] = copy(event)
                    break
            else: # if we didn't match this event
                maybe_unmatched.append(event)
        
        # this breaks peeking, should probably use stack instead of iterator
        self.iterator = chain(maybe_unmatched, self.iterator)
        return results

    def find_matching_sorted(self, target_events, max_gap_size=None, max_unmatched=None):
        target_events = copy(target_events)
        result = []

        if max_unmatched is not None:
            self.unmatched = self.unmatched[-max_unmatched:]

        for i, event in enumerate(self.unmatched):
            for j, target_event in enumerate(target_events):
                if event.is_similar(target_event):
                    self.unmatched[i] = None
                    if event.symbol == "U":
                        event.symbol = "M-" + str(target_event.pos)
                    event = copy(event)
                    event.symbol = "!"
                    result.append((target_event, event))
                    target_events[j] = None
                    break
        # clean up unmatched (no deletion during iteration)
        self.unmatched = [x for x in self.unmatched if x is not None]

        maybe_unmatched = []
        while (max_gap_size is None or len(maybe_unmatched) <= max_gap_size) and any(target_events):
            try:
                event = self.get_next()
            except StopIteration:
                break
            for j, target_event in enumerate(target_events):
                if event.is_similar(target_event):
                    # store unmatched
                    for unmatched_event in maybe_unmatched:
                        unmatched_event.symbol = "U"
                        result.append((None, unmatched_event))
                    self.unmatched += maybe_unmatched
                    maybe_unmatched = []
                    result.append((target_event, event))
                    target_events[j] = None
                    break
            else: # if we didn't match this event
                maybe_unmatched.append(event)
        
        # this breaks peeking, should probably use stack instead of iterator
        self.iterator = chain(maybe_unmatched, self.iterator)
        return result + [(unmatched_target, None) for unmatched_target in target_events if unmatched_target is not None]

def show_event(event):
    if event is None:
        return Event.TEMPLATE.format("", "", "", "", "")
    return str(event)

def match(gold, others, print_unmatched=False, sort_by=None, max_gap_size=None, max_unmatched=None):
    gold_iter = TrackIterator(gold)
    other_iters = [TrackIterator(other) for other in others]

    while True:
        try:
            gold_events = gold_iter.get_next_events()
        except StopIteration:
            break
        matched = []
        for other_iter in other_iters:
            matched.append(other_iter.find_matching(gold_events, max_gap_size, max_unmatched))
        block = zip(gold_events, *matched)
        if sort_by is not None:
            block = sorted(block, key=lambda x: x[sort_by].time if x[sort_by] is not None else INF)
        for pair in block:
            print(*map(show_event, pair))
        if print_unmatched:
            for i, other_iter in enumerate(other_iters):
                if other_iter.unmatched: # These are filtered through max_unmathed
                    print("Currently unmatched in {}:".format(i + 1), *(x.pos for x in other_iter.unmatched))
        print((str.translate(show_event(None), str.maketrans({' ': '-', '|': '+'})) + "-") * (len(others) + 1))

def match_two_sorted(gold, other, max_gap_size=None, max_unmatched=None):
    gold_iter = TrackIterator(gold)
    other_iter = TrackIterator(other)
    all_matched = []

    while True:
        try:
            gold_events = gold_iter.get_next_events()
        except StopIteration:
            break
        all_matched.append(other_iter.find_matching_sorted(gold_events, max_gap_size, max_unmatched))
        matched = all_matched[-1]

        #for pair in matched:
        #    print(*map(show_event, pair))
        #print((str.translate(show_event(None), str.maketrans({' ': '-', '|': '+'})) + "-") * 2)
        #print("Unm: ", *map(show_event, other_iter.unmatched))

    count_all = 0
    count_wrong = 0
    for matched in all_matched:
        for pair in matched:
            print(*map(show_event, pair))
        print((str.translate(show_event(None), str.maketrans({' ': '-', '|': '+'})) + "-") * 2)

    print("Unmatched: ", end="")
    while True:
        try:
            print(show_event(other_iter.get_next()), end=" ")
        except StopIteration:
            break
    print()

    return all_matched

def match_levenshtein(gold, other):
    class Action(Enum):
        MATCH = 1
        REMOVE = 2
        ADD = 3

    distances = [[None] * len(other) for _ in gold]

    for i, gold_event in enumerate(gold):
        for j, other_event in enumerate(other):
            if i == 0:
                distances[i][j] = (j, Action.REMOVE)
                continue
            if j == 0:
                distances[i][j] = (i, Action.ADD)
                continue

            if gold_event.is_similar(other_event):
                distances[i][j] = (distances[i - 1][j - 1][0], Action.MATCH)
            elif distances[i - 1][j][0] < distances[i][j - 1][0]:
                distances[i][j] = (1 + distances[i - 1][j][0], Action.ADD)
            else:
                distances[i][j] = (1 + distances[i][j - 1][0], Action.REMOVE)
    
    result = []

    pos = (len(gold) - 1, len(other) - 1)
    while pos != (0, 0):
        dist, action = distances[pos[0]][pos[1]]
        if action == Action.MATCH:
            result.append(other[pos[1]])
            pos = (pos[0] - 1, pos[1] - 1)
        elif action == Action.REMOVE:
            event = copy(other[pos[1]])
            event.symbol = "-"
            result.append(event)
            pos = (pos[0], pos[1] - 1)
        elif action == Action.ADD:
            event = copy(gold[pos[0]])
            event.symbol = "+"
            result.append(event)
            pos = (pos[0] - 1, pos[1])
    
    return reversed(result)

if __name__ == '__main__':
    # Chopin -> track 1
    # Schubert -> track 0
    #filenames = ["chopin_etude_10_3.mid"] + ["Chopin_op10_no3_p{:0>2}.mid".format(i) for i in range(1, 23)] + ["Chopin_op10_no3_p23-average.mid"]
    #tracks = [preprocess(midi.read_midifile(filename)[1]) for filename in filenames]
    base_names = ["Chopin_op10_no3", "Chopin_op38", "Mozart_K331_1st-mov", "Schubert_D783_no15"]
    base_name = base_names[3]
    recording = 2
    filenames = [
            "../data/match_midi/{}_score.mid".format(base_name),
            "../data/match_midi/{}_p{:0>2}.mid".format(base_name, recording)
        ]
    print(filenames)
    tracks = [preprocess(midi.read_midifile(filename)[0]) for filename in filenames]
#    for group in group_events(tracks[0]): print(*map(show_event, group))
#    for event in preprocess(midi.read_midifile("../data/midi/Schubert_D783_no15_p22.mid")):
#        print(event)
#    print("\n".join(map(show_event, match_levenshtein(tracks[0], tracks[1]))))
#    match(tracks[0], tracks[1:], print_unmatched=False, sort_by=1, max_gap_size=15)
    all_matched = match_two_sorted(tracks[0], tracks[1], max_gap_size=10, max_unmatched=20)
    aligned_gold = [g for g, _ in sum(all_matched, []) if g is not None]
    print("\n".join(map(show_event, match_levenshtein(aligned_gold, tracks[1]))))
