"""Procedurally synthesised chiptune background music.

Generates short (≈8 sec) looping 8-bit tracks in memory and exposes them as
pygame.mixer.Sound objects with `loops=-1`. Two voices: pulse-wave lead +
square-wave bass. No external assets.

Six tracks: menu / stage1 (jungle) / stage2 (caves) / stage3 (base) / boss /
victory. Tracks are pre-generated lazily on first play to avoid blocking
startup."""
import math
import struct
import pygame

SAMPLE_RATE = 22050


# --- musical helpers ---------------------------------------------------------

_A4 = 440.0
_NOTE_NAMES = {'C': -9, 'C#': -8, 'Db': -8, 'D': -7, 'D#': -6, 'Eb': -6,
               'E': -5, 'F': -4, 'F#': -3, 'Gb': -3, 'G': -2, 'G#': -1,
               'Ab': -1, 'A': 0, 'A#': 1, 'Bb': 1, 'B': 2}


def _note_freq(name):
    """Convert 'C4', 'A#3', 'rest' to Hz. 0 Hz means rest."""
    if name == "-" or name is None:
        return 0.0
    # split letter+optional accidental, then octave digit
    n = name.rstrip("0123456789")
    octv = int(name[len(n):])
    semitones = _NOTE_NAMES[n] + (octv - 4) * 12
    return _A4 * (2 ** (semitones / 12.0))


def _pulse_note(freq, samples, duty=0.5, vol=0.25, attack=0.01, release=0.08):
    """Render a pulse-wave note of `samples` length into a list."""
    if freq <= 0 or samples <= 0:
        return [0.0] * max(0, samples)
    out = [0.0] * samples
    period = max(2.0, SAMPLE_RATE / freq)
    threshold = period * duty
    atk_samps = int(SAMPLE_RATE * attack)
    rel_samps = int(SAMPLE_RATE * release)
    sustain_end = max(atk_samps, samples - rel_samps)
    for i in range(samples):
        ph = i % period
        v = vol if ph < threshold else -vol
        # envelope
        if i < atk_samps:
            e = i / max(1, atk_samps)
        elif i < sustain_end:
            e = 1.0
        else:
            e = max(0.0, 1.0 - (i - sustain_end) / max(1, rel_samps))
        out[i] = v * e
    return out


def _triangle_note(freq, samples, vol=0.35, release=0.05):
    if freq <= 0 or samples <= 0:
        return [0.0] * max(0, samples)
    out = [0.0] * samples
    period = max(2.0, SAMPLE_RATE / freq)
    rel = int(SAMPLE_RATE * release)
    sustain_end = max(1, samples - rel)
    for i in range(samples):
        ph = (i % period) / period
        if ph < 0.5:
            v = -1 + 4 * ph
        else:
            v = 3 - 4 * ph
        if i >= sustain_end:
            e = max(0.0, 1.0 - (i - sustain_end) / max(1, rel))
        else:
            e = 1.0
        out[i] = vol * v * e
    return out


def _noise_kick(samples, vol=0.25):
    """Short noisy thump used as a 'kick'."""
    if samples <= 0:
        return []
    out = [0.0] * samples
    import random
    rng = random.Random(7)
    for i in range(samples):
        env = max(0.0, 1.0 - i / samples) ** 2
        out[i] = vol * env * (rng.random() * 2 - 1)
    return out


def _add(buf, snippet, offset):
    if offset < 0:
        snippet = snippet[-offset:]
        offset = 0
    for i, v in enumerate(snippet):
        idx = offset + i
        if idx >= len(buf):
            break
        buf[idx] += v


def _render_track(lead, bass=None, kick_pattern=None, tempo_bpm=140,
                  lead_duty=0.5, lead_vol=0.22, bass_vol=0.30):
    """Render a track.

    `lead` and `bass` are lists of (note_name, beats). `kick_pattern` is a list
    of 0/1 over 16th notes for the duration of `lead`. Returns float buffer."""
    sec_per_beat = 60.0 / tempo_bpm
    total_beats = sum(b for _, b in lead)
    total_samples = int(SAMPLE_RATE * sec_per_beat * total_beats)
    buf = [0.0] * total_samples

    # lead voice
    cursor = 0
    for note, beats in lead:
        nlen = int(SAMPLE_RATE * sec_per_beat * beats)
        snippet = _pulse_note(_note_freq(note), nlen, duty=lead_duty,
                              vol=lead_vol)
        _add(buf, snippet, cursor)
        cursor += nlen

    # bass voice
    if bass:
        cursor = 0
        for note, beats in bass:
            nlen = int(SAMPLE_RATE * sec_per_beat * beats)
            snippet = _triangle_note(_note_freq(note), nlen, vol=bass_vol)
            _add(buf, snippet, cursor)
            cursor += nlen

    # kicks on 16th grid
    if kick_pattern:
        sixteenth = sec_per_beat / 4.0
        kick_dur = int(SAMPLE_RATE * 0.05)
        for i, hit in enumerate(kick_pattern):
            if hit:
                off = int(i * sixteenth * SAMPLE_RATE)
                _add(buf, _noise_kick(kick_dur, vol=0.18), off)

    # normalise softly to prevent clipping
    peak = max((abs(x) for x in buf), default=1.0) or 1.0
    if peak > 1.0:
        buf = [x / peak for x in buf]
    return buf


def _to_int16(samples):
    out = bytearray()
    for s in samples:
        v = max(-1.0, min(1.0, s))
        out += struct.pack('<h', int(v * 30000))
    return bytes(out)


# --- track recipes ------------------------------------------------------------

def _menu_track():
    # A minor — calm-but-arcadey looping motif
    lead = [
        ("A4", 1), ("C5", 1), ("E5", 1), ("A5", 1),
        ("G5", 0.5), ("E5", 0.5), ("D5", 1), ("E5", 1),
        ("A4", 1), ("C5", 1), ("E5", 1), ("G5", 1),
        ("F5", 0.5), ("E5", 0.5), ("D5", 1), ("C5", 1),
    ]
    bass = [("A2", 4), ("F2", 4), ("E2", 4), ("A2", 4)]
    return _render_track(lead, bass=bass, tempo_bpm=110,
                         lead_duty=0.25, lead_vol=0.18, bass_vol=0.28)


def _jungle_track():
    # adventurous E minor pentatonic
    lead = [
        ("E4", 0.5), ("G4", 0.5), ("B4", 0.5), ("D5", 0.5),
        ("E5", 1), ("D5", 0.5), ("B4", 0.5),
        ("G4", 0.5), ("B4", 0.5), ("D5", 0.5), ("E5", 0.5),
        ("D5", 1), ("B4", 1),
        ("A4", 0.5), ("G4", 0.5), ("E4", 0.5), ("G4", 0.5),
        ("B4", 1), ("E5", 1),
        ("D5", 0.5), ("B4", 0.5), ("G4", 0.5), ("E4", 0.5),
        ("G4", 1), ("E4", 1),
    ]
    bass = [
        ("E2", 2), ("E3", 2),
        ("G2", 2), ("G3", 2),
        ("A2", 2), ("A3", 2),
        ("B2", 2), ("B3", 2),
    ]
    kick = [1, 0, 0, 0, 1, 0, 0, 0,
            1, 0, 0, 0, 1, 0, 0, 0,
            1, 0, 0, 0, 1, 0, 0, 0,
            1, 0, 0, 0, 1, 0, 0, 0]
    return _render_track(lead, bass=bass, kick_pattern=kick, tempo_bpm=140,
                         lead_duty=0.5, lead_vol=0.18, bass_vol=0.28)


def _caves_track():
    # dark D minor — slower, more space
    lead = [
        ("D4", 1), ("F4", 1), ("A4", 1), ("D5", 1),
        ("C5", 1), ("A4", 1), ("F4", 1), ("D4", 1),
        ("A3", 1), ("D4", 1), ("F4", 1), ("A4", 1),
        ("G4", 1), ("F4", 1), ("E4", 1), ("D4", 1),
    ]
    bass = [
        ("D2", 4),
        ("A2", 4),
        ("Bb2", 4),
        ("F2", 4),
    ]
    kick = ([1, 0, 0, 0, 0, 0, 1, 0] * 8)
    return _render_track(lead, bass=bass, kick_pattern=kick, tempo_bpm=96,
                         lead_duty=0.5, lead_vol=0.16, bass_vol=0.26)


def _base_track():
    # tense, fast — F minor with chromatic motion
    lead = [
        ("F4", 0.5), ("F4", 0.5), ("Ab4", 0.5), ("F4", 0.5),
        ("C5", 0.5), ("Bb4", 0.5), ("Ab4", 0.5), ("G4", 0.5),
        ("F4", 0.5), ("F4", 0.5), ("Ab4", 0.5), ("F4", 0.5),
        ("Eb5", 0.5), ("C5", 0.5), ("Bb4", 0.5), ("Ab4", 0.5),
        ("F4", 0.5), ("F4", 0.5), ("G4", 0.5), ("Ab4", 0.5),
        ("C5", 0.5), ("Bb4", 0.5), ("Ab4", 0.5), ("G4", 0.5),
        ("F4", 0.5), ("Ab4", 0.5), ("C5", 0.5), ("F5", 0.5),
        ("Eb5", 0.5), ("C5", 0.5), ("Bb4", 0.5), ("Ab4", 0.5),
    ]
    bass = [
        ("F2", 2), ("F3", 2),
        ("F2", 2), ("Ab2", 2),
        ("Eb2", 2), ("Eb3", 2),
        ("Bb2", 2), ("F2", 2),
    ]
    kick = ([1, 0, 1, 0] * 16)
    return _render_track(lead, bass=bass, kick_pattern=kick, tempo_bpm=150,
                         lead_duty=0.5, lead_vol=0.18, bass_vol=0.30)


def _boss_track():
    # boss alarm — chromatic descent in D minor
    lead = [
        ("D5", 0.5), ("C5", 0.5), ("B4", 0.5), ("A4", 0.5),
        ("D5", 0.5), ("C5", 0.5), ("B4", 0.5), ("A4", 0.5),
        ("D5", 0.25), ("D5", 0.25), ("F5", 0.5), ("E5", 0.5), ("D5", 0.5),
        ("C5", 0.5), ("Bb4", 0.5), ("A4", 1),
    ]
    bass = [
        ("D2", 2), ("D2", 2),
        ("A2", 2), ("D3", 2),
    ]
    kick = ([1, 0, 1, 0, 1, 0, 1, 0] * 4)
    return _render_track(lead, bass=bass, kick_pattern=kick, tempo_bpm=160,
                         lead_duty=0.25, lead_vol=0.22, bass_vol=0.30)


def _sky_track():
    # bright, anthemic — A major-ish
    lead = [
        ("A4", 0.5), ("E5", 0.5), ("A5", 1),
        ("G#5", 0.5), ("E5", 0.5), ("C#5", 1),
        ("D5", 0.5), ("F#5", 0.5), ("A5", 1),
        ("G#5", 0.5), ("E5", 0.5), ("C#5", 1),
        ("E5", 0.5), ("A5", 0.5), ("C#6", 1),
        ("B5", 0.5), ("A5", 0.5), ("F#5", 1),
        ("E5", 0.5), ("D5", 0.5), ("C#5", 0.5), ("B4", 0.5),
        ("A4", 2),
    ]
    bass = [
        ("A2", 2), ("A3", 2),
        ("F#2", 2), ("F#3", 2),
        ("D2", 2), ("D3", 2),
        ("E2", 2), ("E3", 2),
    ]
    kick = ([1, 0, 0, 1, 0, 0, 1, 0] * 8)
    return _render_track(lead, bass=bass, kick_pattern=kick, tempo_bpm=130,
                         lead_duty=0.25, lead_vol=0.20, bass_vol=0.28)


def _victory_track():
    # ascending fanfare in C major
    lead = [
        ("C5", 0.5), ("E5", 0.5), ("G5", 0.5), ("C6", 1.5),
        ("B5", 0.5), ("G5", 0.5), ("E5", 0.5), ("G5", 1.5),
        ("F5", 0.5), ("A5", 0.5), ("C6", 0.5), ("F6", 1.5),
        ("E6", 0.5), ("D6", 0.5), ("C6", 0.5), ("G5", 0.5), ("C6", 1),
    ]
    return _render_track(lead, tempo_bpm=130,
                         lead_duty=0.5, lead_vol=0.22)


class MusicPlayer:
    """Lazy synth + playback. Holds the currently-playing Sound on its own
    pygame.mixer.Channel so SFX (on default channel) don't fight it."""

    TRACKS = {
        "menu": _menu_track,
        "jungle": _jungle_track,
        "caves": _caves_track,
        "base": _base_track,
        "sky": _sky_track,
        "boss": _boss_track,
        "victory": _victory_track,
    }

    def __init__(self):
        self._sounds = {}
        self._current = None
        self.channel = None
        self.enabled = False
        try:
            if pygame.mixer.get_init() is not None:
                # reserve one channel for music so SFX don't clobber it
                if pygame.mixer.get_num_channels() < 4:
                    pygame.mixer.set_num_channels(4)
                self.channel = pygame.mixer.Channel(3)
                self.channel.set_volume(0.55)
                self.enabled = True
        except Exception:
            self.enabled = False

    def _get(self, name):
        if name in self._sounds:
            return self._sounds[name]
        recipe = self.TRACKS.get(name)
        if recipe is None:
            return None
        try:
            samples = recipe()
            snd = pygame.mixer.Sound(buffer=_to_int16(samples))
            self._sounds[name] = snd
            return snd
        except Exception as e:
            print(f"[music] failed to build '{name}': {e}")
            return None

    def play(self, name, loop=True):
        if not self.enabled or self.channel is None:
            return
        if name == self._current:
            return
        snd = self._get(name)
        if snd is None:
            return
        self.channel.stop()
        self.channel.play(snd, loops=-1 if loop else 0)
        self._current = name

    def stop(self):
        if not self.enabled or self.channel is None:
            return
        self.channel.stop()
        self._current = None

    def set_paused(self, paused):
        if not self.enabled or self.channel is None:
            return
        try:
            if paused:
                self.channel.pause()
            else:
                self.channel.unpause()
        except Exception:
            pass

    def set_muted(self, muted):
        if not self.enabled or self.channel is None:
            return
        try:
            self.channel.set_volume(0.0 if muted else 0.55)
        except Exception:
            pass
