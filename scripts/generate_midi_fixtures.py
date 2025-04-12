import pretty_midi
import os

# Ensure the fixtures directory exists
fixtures_dir = "tests/fixtures"
os.makedirs(fixtures_dir, exist_ok=True)

# --- 1. simple_melody.mid ---
simple_midi = pretty_midi.PrettyMIDI()
piano_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')
piano = pretty_midi.Instrument(program=piano_program)

# Add notes (pitch, velocity, start_time, end_time)
notes_simple = [
    (60, 100, 0.0, 0.5), # C4
    (62, 100, 0.5, 1.0), # D4
    (64, 100, 1.0, 1.5), # E4
    (65, 100, 1.5, 2.0), # F4
]
for pitch, velocity, start, end in notes_simple:
    note = pretty_midi.Note(velocity=velocity, pitch=pitch, start=start, end=end)
    piano.notes.append(note)

simple_midi.instruments.append(piano)
simple_midi.write(os.path.join(fixtures_dir, "simple_melody.mid"))
print("Generated tests/fixtures/simple_melody.mid")

# --- 2. multi_track.mid ---
multi_midi = pretty_midi.PrettyMIDI()
# Instrument 1: Piano
piano_multi = pretty_midi.Instrument(program=piano_program, name="Piano Track")
notes_piano = [
    (60, 100, 0.0, 0.4), # C4
    (64, 100, 0.5, 0.9), # E4
    (67, 100, 1.0, 1.4), # G4
]
for pitch, velocity, start, end in notes_piano:
    note = pretty_midi.Note(velocity=velocity, pitch=pitch, start=start, end=end)
    piano_multi.notes.append(note)
multi_midi.instruments.append(piano_multi)

# Instrument 2: Flute
flute_program = pretty_midi.instrument_name_to_program('Flute')
flute_multi = pretty_midi.Instrument(program=flute_program, name="Flute Track")
notes_flute = [
    (72, 90, 0.2, 0.7), # C5
    (76, 90, 0.8, 1.3), # E5
    (79, 90, 1.4, 1.9), # G5
]
for pitch, velocity, start, end in notes_flute:
    note = pretty_midi.Note(velocity=velocity, pitch=pitch, start=start, end=end)
    flute_multi.notes.append(note)
multi_midi.instruments.append(flute_multi)

multi_midi.write(os.path.join(fixtures_dir, "multi_track.mid"))
print("Generated tests/fixtures/multi_track.mid")

# --- 3. empty.mid ---
empty_midi = pretty_midi.PrettyMIDI()
# No instruments or notes added
empty_midi.write(os.path.join(fixtures_dir, "empty.mid"))
print("Generated tests/fixtures/empty.mid")

print("MIDI fixture generation complete.")