# Building a Heartbeat Installation Sample Library on Freesound.org

Your interactive heartbeat installation needs **clean, sustained, pitch-shiftable samples** from five timbral families. Freesound.org offers over 400,000 Creative Commons samples,  with the Music Technology Group’s professional collections  and specialized user libraries providing exceptional quality. **Start with CC0-licensed single-note samples from MTG, sgossner, and juskiddink for guaranteed quality and maximum legal flexibility**. This search plan identifies 50+ specific high-quality samples with IDs, optimal search terms for each timbral family, and concrete evaluation criteria to efficiently build a versatile 80-120 sample library suitable for any harmonic framework through pitch-shifting.

The challenge: Freesound is community-uploaded with inconsistent quality requiring careful filtering. The opportunity: Academic institutions and professional sound designers have contributed systematic, high-quality multisamples perfect for installations. Success depends on knowing exactly what to search for, what technical specifications matter, and which pitfalls destroy pitch-shifting quality.

## Freesound.org platform essentials for installation-quality samples

Freesound.org offers powerful search capabilities beyond basic keyword matching.   **Use advanced filtering to surface quality samples quickly**: combine `filter=license:"Creative Commons 0" type:(wav OR flac) samplerate:[44100 TO *] bitdepth:[24 TO *] avg_rating:[3.5 TO *]` with relevant search terms. Sort results by rating or downloads first—popular samples indicate community validation since anyone can upload. The April 2025 Broad Sound Taxonomy update provides structured categories,  though user tags remain more relevant for finding specific characteristics.

**Technical quality indicators matter critically for pitch-shifting**. Preview audio uses compressed 64-128kbps encoding, but downloaded files retain original quality. Target WAV or FLAC formats at 44.1kHz minimum (48kHz or 96kHz ideal for extreme transposition), 24-bit depth preferred over 16-bit for headroom. The platform displays complete technical specifications on each sample page including microphone details—look for professional equipment mentions (Neumann U87, Rode NT series, Zoom H4n/H6) as quality signals.

For installation use, **prioritize CC0 (public domain) licensing for zero restrictions** or CC Attribution for commercial-compatible use requiring simple credits. Filter exclusively by CC0 to avoid attribution complexity in public installations. The platform provides an attribution list generator at freesound.org/home/attribution/ to track downloaded sounds.  Avoid CC BY-NC (NonCommercial) licenses if your installation has any revenue component, and never use samples with NoDerivatives clauses since pitch-shifting constitutes derivative work.

Content-based search using Essentia audio analysis enables filtering by acoustic properties: `descriptors_filter=lowlevel.pitch.mean:[219 TO 221]` finds specific notes, while `duration:[0.8 TO 2.0]` narrows to your ideal sustain range.   Combine text search with technical filters and tags like “single-note”, “sustained”, “clean”, and “dry” for efficient discovery.  The MTG (Music Technology Group) at Universitat Pompeu Fabra provides the most consistent professional quality—search for user “MTG” or tags containing “good-sounds” to access their systematically recorded instrument collections. 

## Metallic and bell-like sounds: singing bowls, tubular bells, chimes, gongs

Metallic percussion offers the longest natural sustains and clearest pitch content for your installation. **Singing bowls and crystal bowls provide meditative resonance ideal for heartbeat applications**,  with clean fundamentals that pitch-shift exceptionally well. Tubular bells deliver orchestral quality with precise pitch definition, while gongs add deep, immersive bass content.

### Best samples and where to find them

**Start with sgossner’s Orchestral Chimes pack (#12231)**: professionally sampled tubular bells covering chromatic range C4-F5. Sample ID 374273 (Tubular Bells C4) exemplifies the quality—16-bit/44.1kHz stereo WAV, CC0 license, recorded with Rode NT1-A spaced pair in large auditorium with 1.5-second sustain and clear overtone structure.  The pack includes multiple mic positions (close + room) for flexibility. All samples are public domain with consistent recording technique.

For **singing bowls, juskiddink’s titanium bowl (ID 122650)** delivers exceptional 84-second sustain with 24-bit/44.1kHz quality. The 10.5cm bowl was palm-balanced during recording to reduce ambient noise, struck once, creating a clean fundamental with natural decay perfect for pitch manipulation.  Alternative: ID 439235 by zambolino offers 35-second sustain, 24-bit quality, CC0 licensing, and user descriptions praising its “powerful” clean fundamental. For shorter meditative strikes, ID 193022 (Tibetan Singing Bowl by Truthiswithin) provides clean 1-second sustain in CC0,  recorded with an 8cm bowl and wood striker. 

**Crystal bowls** add ethereal quality: juskiddink’s quartz bowl (ID 129219) sustains for 3:46 minutes as a continuous drone texture in Note D, recorded from underneath for full resonance capture.  This rubbed/sung technique creates sustained background layers rather than percussive hits.

**Gongs supply deep resonance**: juskiddink’s 22-inch Paiste symphonic gong (ID 86773) recorded with Rode NT4 into Zoom H4 provides 2+ second decay with professional quality. Users describe it as “perfect” and “lovely sound.” For higher sample rates, Omachronic’s entrance gong (ID 130346) at 96kHz/16-bit stereo offers long dramatic decay ideal for transposition, though one user noted clipping—check waveform before use. 

**Hand bells** provide bright accents: InspectorJ’s Hand Bells pack (#19255) contains chromatic singles like ID 339818 (Note G, 0.8-second decay, CC Attribution 4.0) recorded professionally with Zoom H1 V2.  For explicitly cleaned samples, steaq’s Bright Tibetan Bell (ID 346328, Note B) underwent frequency editing in Audacity—optimized 1+ second sustain, CC0.

### Search strategy and tags

Search terms yielding best results: **“singing bowl” + “single note”**, **“tubular bells”**, **“crystal bowl”**, **“gong strike”**, **“hand bell” + “single”**.  Combine with tags: “sustained”, “resonant”, “clean”, “single-note”, “meditation”. Use pack searches for systematic collections—browse sgossner’s 461 packs, juskiddink’s professional instrument recordings, or InspectorJ’s organized chromatic sets.

Look for descriptions mentioning **specific materials (titanium, quartz, bronze)**, instrument dimensions, and recording equipment. Phrases like “single strike”, “clean recording”, “no effects”, and specific note names (C4, D, G) indicate quality. User comments praising “clear”, “professional”, or “resonant” qualities provide community validation.

### Quality criteria and common pitfalls

**Ideal characteristics**: 0.8-2+ second sustain with natural exponential decay, clear fundamental frequency, moderate harmonic complexity (not dense inharmonic partials), strong attack transient for rhythmic precision, minimal background noise. 24-bit depth provides headroom for gain adjustment post-shift, while 48kHz+ sample rates preserve harmonics during extreme transposition.

**Avoid these issues**: Excessive reverb or room ambience (reverb doesn’t pitch-shift naturally, creates muddy artifacts—search “dry” or “close mic”), background noise (field recordings with audience chatter, wind, HVAC hum—noise floor becomes audible when pitched down), multiple strikes or melodic sequences (need isolated single notes, not “Pentatonic Singing Bowl Scale Demo” ID 435929), overly complex overtone structures described as “discordant” or “atonal”, clipping/distortion (check user comments for warnings, inspect waveforms for flat tops), pre-faded or truncated samples with artificial decay envelopes (look for natural decay descriptions), synthesized sounds rather than acoustic recordings (digital artifacts amplify during shifting), and low-bitrate MP3 files (compression artifacts become audible—prioritize WAV/FLAC).

One user noted on ID 202003: “you cut the end of the decay off”—this truncation limits pitch-shift range. Always verify complete natural decay.

## Wooden percussion: kalimba, marimba, xylophone, tongue drums

Wooden instruments offer warm, organic timbres with good pitch definition and natural resonance. **Kalimbas and marimbas provide rich harmonic content ideal for meditative contexts**, while xylophones add brightness. These materials pitch-shift cleanly when recordings capture clear fundamentals.

### Best samples and where to find them

**Kalimba samples excel at sustained resonance**. ID 331047 (Kalimba C-note by foochie_foochie) delivers nearly 4 seconds of sustain—exceptional for heartbeat timing. Recorded with Rode NT1-A through Scarlett 2i2 at 48kHz/16-bit stereo with professional noise reduction, CC0 licensing provides maximum flexibility.  For richer harmonics, ID 175576 (Note F + harmonics by sergeeo) offers 24-bit depth at 2.5-second duration with condenser mic and tube pre-amp recording.   The description explicitly notes “harmonic content,” making it ideal for pitch manipulation.

For **authentic African character**, arioke’s Tanzanian kalimba pack (#3759) includes ID 58715 (C4, 1.8-second sustain) with earthy, round tone and natural buzz adding character.  Close-mic’d with Behringer C-2 condenser,  these dry recordings under Sampling+ license (very permissive) provide organic material.

**Marimba samples from sgossner’s VSCO 2 CE project** represent concert hall quality. ID 255689 (Marimba G4/MIDI 67) provides 2.2 seconds of natural decay recorded with stereo Rode NT1-A mid mics in concert hall at 24-bit/44.1kHz.  The professional sampling project documents each note precisely—CC Attribution 3.0. ID 255681 (Marimba C7/MIDI 96) offers bright, high-register tone at 1.7 seconds   for ethereal highlights. 

**Xylophone chime bars from DANMITCH3LL’s pack (#14220)** deliver bell-like ring. ID 232002 (Xylophone C) provides 3.75 seconds of excellent resonance with attack trimmed for smoother hits—ideal for pitch-shifting. Recorded with Rode M5 XY stereo pair at 16-bit/44.1kHz,  the full pack contains complete C-major scale (7 notes, all 3-4 second sustain) under CC Attribution 3.0. 

**Tongue drums** add meditative steel tones: ID 381955 (Steel Tongue Drum by elliotrambach) captures a 4:09 performance near Lake Michigan with field recording ambience.   Extract individual notes with excellent sustain and meditative quality, CC0 licensed at 16-bit/44.1kHz stereo.

### Search strategy and tags

Most effective terms: **“kalimba single note”**, **“marimba single” or “marimba note”**, **“xylophone single note clean”**, **“tongue drum”**, **“log drum”**. Include specific note names like “C4” or “G4” to find pitched samples. Combine with tags “single-note”, “multisample”, “sustain”, “clean”, “dry”, “resonance”.

Search specific high-quality collections: **“VSCO 2 CE”** returns professional orchestral samples (public domain), user **sgossner/Samulis** for systematic multisamples, **arioke** for authentic African instruments. Use site operator `site:freesound.org kalimba single note` for focused results.

Look for descriptions mentioning **microphone models**, audio interfaces, recording environments (studio, treated room), sample rates 44.1kHz+, bit depth specifications. Keywords indicating quality: “clean”, “dry”, “no reverb”, “sustain”, “resonance”, specific pitch notation (C4, MIDI Note 60, 440Hz), “noise-reduced”, professional markers like “part of sample pack/library”, multiple round-robins or velocity layers, detailed file naming conventions.

### Quality criteria and common pitfalls

**Ideal characteristics for wooden percussion**: Clear fundamental with some pitch content (not just percussive attack), 0.8-2 second sustain or good resonance, simple harmonic structure without excessive complexity, warm organic timbre appropriate for meditation, natural decay envelope. Technical specs: WAV format at 44.1kHz+, 16-bit minimum (24-bit preferred), stereo adds spatial depth, clean recording with minimal unwanted noise.

**Common issues to avoid**: Samples too short/percussive with insufficient sustain (standard wood blocks under 0.5 seconds become too brief when pitched down—exception: may work for brief accents between sustained tones), multiple notes in melodic sequences (chords, arpeggios, scales without gaps cannot pitch-shift cleanly—creates dissonant clusters), poor recording quality with background noise, distortion, clipping (check comments for “noise”, “hiss”, “distortion”; avoid “phone recording” or “laptop mic”), overly processed samples with heavy reverb, delay, or effects baked in (effects don’t transpose naturally—prefer “dry” recordings), licensing restrictions (CC BY-NC NonCommercial problematic if installation has any commercial aspect), samples in wrong pitch range (extreme high registers above C7 become too thin when pitched down; very low samples become muddy when pitched lower—middle registers C3-C6 provide most flexibility), unrealistic timbres described as “toy”, “kid’s”, or “plastic” that break meditative atmosphere.

Watch for duration specifications. ID 167164 (Cedar Kalimba 29-second scale by ultradust) contains complete diatonic C-major scale requiring note extraction with good spacing. This 24-bit Zoom H4n recording  provides excellent material but needs editing. 

## Synthesizer tones: pads, plucks, ambient drones

Synth samples offer the cleanest pitch-shifting potential when properly selected. **Simple waveforms and analog synthesis without built-in modulation shift with zero artifacts**, making them ideal for creating harmonic collections. The 40,000+ sample Modular Samples library provides systematic, professional-quality analog synth recordings all licensed CC0. 

### Best samples and where to find them

**The Modular Samples library represents the highest quality source**. User **modularsamples** has uploaded 461 packs of professional analog synthesizer multisamples.  Korg Mono-Poly Synth Bass pack (#17384, ID 295334 example) delivers clean analog bass synthesis with simple harmonic content and 2-second sustain—excellent for minimal artifacts.  The systematic pack spans multiple octaves, all CC0. Elektron Analog Four pack (#17263, 21 samples C1-C7) provides modern analog synthesis with 10+ second duration, exceptional stability, 24-bit quality.  DSI Tetra “Sample and Hold Me” pack (#17258, 48 samples) offers complex but stable analog timbres with 9+ second sustains and interesting harmonic movement that shifts cleanly.

For **ambient pads**, Jovica’s PPG collections deliver ethereal sustained synthesis. ID 6251/6256 (PPG Sustained Organwave pack #319, 16 samples) provides organ-like 8-second sustained tones from Waldorf PPG VST with unusual attack adding character— very good pitch-shifting quality from clean digital synthesis (CC Attribution 3.0).  The Space Drone series (ID 46098 SpaceDrone 04, plus 46097, 46026, 46035) creates pure ambient space with Reaktor Space Drone+ synth, FLAC 16-bit/44.1kHz, 1-5 minute durations—exceptional meditative quality designed for ambient applications (CC Attribution 3.0).   Note some include “laser-like” or “radio frequency” textures requiring audition.

**Dark ambient drones** add immersive depth: martinbeltov’s Dark Ambient Drone (ID 244196, 49 seconds) uses VST synthesis for dark but not harsh tone with clean synthesis and full sustain, CC0.  PatrickLieberkind’s version (ID 396457, 59 seconds) provides deep pulsing drone from FL Studio with inherent 60 BPM-ish pulse—may or may not suit your needs.  

For **maximum pitch-shift cleanness**, Jovica’s Basic Sine Wave pack (ID 8795, 16 samples C1-C6) offers pure sine waves with minimal delay—simplest harmonic content means perfect shifting with zero artifacts. Created with Reaktor Theremin emulation at 2-second duration (CC Attribution 3.0).  

**Pluck sounds** for more percussive triggers: Korg Z1 Plinky pack (#17413, 61 samples) provides clean 3-second plucks from analog modeling synthesis with excellent attack and sustained decay (CC0). 

### Search strategy and tags

Most effective searches: **“synth pad sustained single note”**, **“PPG sustained”**, **“ambient drone synth”**, **“modulated samples [username]”** to access the 40,000-sample library, **“analog synth” + specific synthesizer names** (Korg, Roland, Moog, DSI). Filter by **tags**: “single-note”, “multisample”, “sustained”, “synthesizer”, “clean”, “CC0”.

Look for **pack searches over individual samples**—multisamples provide organized collections with consistent quality. Browse modularsamples’ 461 packs, Jovica’s systematic instrument collections (PPG multisamples, Space Drones, sine waves).

Descriptions should mention: **simple waveform types** (sine, triangle, sawtooth), **analog synthesizer names and models**, **“no effects” or “minimal processing”**, **“sustained” or “drone”**, duration 0.8-10+ seconds, bit depth 16 or 24-bit, WAV or FLAC format, professional library sources (Modular Samples, VSCO), CC0 or CC Attribution licenses. Professional markers include detailed synthesis method descriptions and systematic note documentation.

### Quality criteria and common pitfalls

**Ideal characteristics**: Single sustained note (not chord or sequence), clean simple waveform or analog synthesis, minimal built-in effects (no baked-in reverb, delay, chorus, flanging), duration 1-10+ seconds, soft attack for smooth heartbeat feel (under 0.1s usually best), stable harmonic content throughout sustain, meditative calming emotional character rather than tense or aggressive. Technical specs: WAV/FLAC format, 44.1kHz+ sample rate, 16-bit minimum (24-bit ideal for dynamic range), mono or stereo based on preference.

**Critical pitfalls destroying pitch-shift quality**: Built-in modulation (LFO vibrato, filter sweeps create pitch instability—avoid tags “LFO”, “vibrato”, “modulated”, “sweeping”), heavy processing (reverb, chorus, flanging creates smearing when shifted—search “clean”, “dry”, “no effects”), complex harmonic content (heavily layered or inharmonic sounds create artifacts—prefer simple waveforms like sine, triangle, saw, single-oscillator patches), percussive attack without sustain (short plucks under 0.8s don’t sustain through heartbeat cycle—check duration, look for “sustained” or “long decay”), sequences vs. single notes (melodic sequences or arpeggios shift incorrectly—always check for “single note” tag), license restrictions (NonCommercial or NoDerivatives limit installation use—prioritize CC0 or CC Attribution), low audio quality (MP3 artifacts, low sample rates amplify during shifting—prefer WAV/FLAC at 44.1kHz+, 16-bit minimum), stereo width issues (wide stereo pads may cause phasing when shifted—test or use mono samples).

Example to avoid: “Epic Synth Pad” ID 244256 where one user reported “weird screech” in background—audition carefully before use.  “Thunder Pad” ID 36179 has intentional modulation/LFO with rumble morphing to musical tone—complex modulation won’t shift cleanly. 

Headphaze’s 20-minute Ambient Drone Solfeggio (ID 235527) designed specifically for meditation with binaural beating offers maximum meditative quality but note complex harmonic structure from mathematical chord composition with changing timbre throughout (CC Attribution 3.0, WAV 16-bit/44.1kHz stereo). 

## Natural and organic sounds: water, stone, breath, body percussion

Organic sounds provide textural contrast and grounding earthiness. **Water drops offer surprisingly clear pitch content**, while stone and wood resonances add primitive, elemental quality. These require careful selection since many natural sounds lack clear pitch definition needed for musical pitch-shifting.

### Best samples and where to find them

**Water drops with pitch content**: ID 536113 (Water Drop Single by EminYILDIRIM) delivers ideal 1.57-second duration with clear resonant tone. Recorded at 24-bit/96kHz with professional Zoom H6,  this clean bright water drop has natural decay and minimal noise (CC Attribution 4.0).  Alternative: ID 174718 (Single Water Drop by paespedro) at 0.47 seconds, 32-bit/44.1kHz stereo—mouth-made sound with clear tone, very natural, CC0 license.   For simple droplets, ID 267221 (Water Droplet by gkillhour) provides 0.5-second clean single drop recorded with Yeti microphone  (CC Attribution 4.0).

**Metallic/resonant percussion from organic materials**: ID 219633 (crotales by andrescompovigo) captures Nepali crotales with 10-second long sustaining resonance recorded with Neumann 184 cardioid— clear pitched bell-like tone with ethereal quality, excellent pitch-shifting (CC0).  Some background noise noted by creator but resonance quality remains excellent. ID 42095 (Bell Meditation by fauxpress) provides 30.5-second pure meditation bell tone with beautiful sustaining resonance—perfect meditative quality in clean recording (CC0 Mp3/44.1kHz/96kbps mono).  ID 158190 (Metal sing bowl resonance by hiddenpersuader) contains multiple hits extractable from professional recording—metal singing bowl with rich harmonics, very organic meditative sound (CC0).

**Bamboo and wood percussion**: ID 386888 (Bamboo hit by michorvath) delivers 0.57-second small bamboo stick hitting table with clean organic tone—percussive with some pitch content (CC0, 16-bit/44.1kHz mono).  ID 66220 (bamboo1 by PercussionFiend) provides excellent 0.5-second single bamboo wind chime piece struck with rubber mallet—specifically processed with noise removal and amplification for clean resonant bamboo tone, great for pitch-shifting (CC0). 

**Stone resonance**: ID 232102 (Stone grind by Thalamus_Lab) offers manipulated field recording with stone grinding resonance— more textural with some pitch elements for variety (CC Attribution 3.0). ID 319226 (Single rock hitting wood by worthahep88) creates natural collision sound with satisfying tone from rock striking wood (CC0).

### Search strategy and tags

Effective terms: **“water drop single”**, **“water droplet”**, **“stone resonance”**, **“rock percussion”**, **“crotales”**, **“bamboo hit”**, **“wooden percussion single”**, **“meditation bell”**, **“bell resonance”**. Include **“singing bowl”**, **“kalimba”**, **“thumb piano”** for metallic organic sounds.

Filter by tags: **“single”**, **“one-shot”**, **“resonance”**, **“clean”**, **“field-recording”**, **“percussion”**, **“natural”**, **“organic”**, **“meditation”**. Avoid tags: “loop”, “background”, “ambience”, “processed”.

Look for descriptions mentioning: **professional microphones** (Zoom H6, Neumann, Yeti), **sample rate 44.1kHz+**, **bit depth 16-bit+**, **“noise-reduced” or “amplified”**, specific materials and recording methods. Browse packs: arioke’s Kalimba pack (#3759) for metallic organic, juskiddink’s Bells and gongs pack (#5069) for resonant objects.

### Quality criteria and common pitfalls

**Ideal characteristics**: Some identifiable pitch content (not pure noise), 0.8-2 second duration with resonance or sustain, clean recording with minimal environmental noise, clear distinct attack, natural decay envelope, organic meditative quality. Technical specs: WAV format preferred, 44.1kHz+ sample rate, 16-bit+ depth, sufficient volume without clipping.

**Common issues**: Environmental noise (traffic, wind, HVAC, background voices destroy clean recording), room reflections (excessive reverb makes sound muddy), microphone handling (bumps, rustling, movement during recording), electrical hum or buzz, over-compression (loss of dynamic range, pumping artifacts), multiple sounds (avoid recordings with several impacts or inconsistent timing), excessive processing (already heavily reverbed or effected samples), low quality (MP3 at low bitrate, poor technique), no sustain (sounds stopping too quickly under 0.5 seconds), pure noise (sounds without clear pitch content won’t shift well musically).

For pitch-shifting specifically avoid: narrow frequency range (sounds lacking harmonics won’t shift musically), transient-only (purely percussive clicks without resonance), already pitch-shifted samples (may have artifacts), overly synthetic digital sounds (shift less naturally than organic sources).

Description red flags include: “noisy recording”, “background sounds”, “needs cleanup”, “processed”, “with effects”, “reverb added”, “multiple takes”, “several hits”, “loop”, no technical specs listed. Always preview before downloading and check waveform for clean attack and natural decay.

## String resonance: bowed strings, plucked strings, harmonics

String instruments provide warm, human emotional quality with excellent sustain and natural musicality. **Non-vibrato recordings are critical**—vibrato creates frequency modulation that becomes jarring when pitch-shifted. The MTG Good-sounds collection offers the most reliable professional quality with clean recordings and clear pitch definition. 

### Best samples and where to find them

**The MTG (Music Technology Group) at Universitat Pompeu Fabra provides exceptional systematic collections**. Search for user “MTG” or tags containing “good-sounds” to access professionally recorded instruments. All samples include precise metadata: concert pitch (442Hz), MIDI note numbers, professional Neumann U87 microphones, 24-bit/48kHz mono recordings. 

**Cello samples excel at meditative sustain**. ID 156664 (Cello C String Resonance by juskiddink)—NOT MTG but exceptional quality—captures open C string after bow lift for pure resonance with 10+ second exceptional sustain. Recorded at 24-bit/44.1kHz stereo with Rode NT4, unprocessed with no vibrato and pure harmonic content. User comment: “The sustain on this is absolutely great” (CC Attribution 4.0).   From MTG: ID 358232 (Cello C4) provides 2.1-second professional single note at 442Hz concert pitch, clean articulation (CC Attribution 3.0).   ID 357949 (Cello D3, 3.78 seconds) offers lower register warm tone with clear low-end fundamental, ideal for downward pitch-shifting (MIDI note 38).   ID 357907 (Cello F2, 4.45 seconds) delivers very deep meditative grounding quality with strong fundamental in low register. 

**Violin samples** add brightness: ID 356134 (Violin C4 by MTG) provides 3.23-second professional Neumann U87 recording at 442Hz concert pitch—clean sustained bow tone, monophonic with clear fundamental (24-bit/48kHz mono, CC Attribution 3.0, MIDI note 48).  

**Pizzicato for percussive strikes**: ID 354309 (Double Bass A1 Pizzicato by MTG) delivers deep 3.51-second pluck with natural resonance—clean attack with rich harmonic decay, MIDI note 33 with very low fundamental excellent for heartbeat pulse (CC Attribution 3.0).  ID 153816 (Double-bass C3 Pizzicato Non-Vibrato by Carlos_Vaquero) provides 2.9-second mid-range pizzicato with mezzoforte dynamic, recorded with Zoom H2N at 442Hz—non-vibrato ensures clean pitch-shifting, though note CC BY-NC (NonCommercial) restriction.  ID 354314 (Double Bass D2 Pizzicato by MTG) offers 3+ second clean low pizzicato with good decay curve. 

**Harmonics for ethereal purity**: ID 183808 (Classical Guitar Harmonic by quartertone) captures pure harmonic at 12th fret, 3rd string (G note, MIDI 67) with 3.13-second duration. Contains crossfade-looped region for sustained use.  Recorded with CAD E100 microphone on Yamaha Eterna guitar—harmonics have pure sine-like quality with minimal overtones, excellent pitch-shifting (CC0, 24-bit/48kHz mono).  The pack contains multiple velocity layers and fret positions. 

**String-like alternatives**: ID 254349 (Vibraphone Bow F-F by cmorris035) creates bowed metal bar tones with bell-like quality—6:58 minute chromatic scale with individual notes sustaining 5-10+ seconds. Recorded with Zoom H4n, used by others for granular sampling and installations.  Pure sustained tones with clear pitch, ethereal quality perfect for meditation (CC0, 16-bit/48kHz mono).  

### Search strategy and tags

Most effective searches: **“MTG cello single note”**, **“MTG violin single note”**, **“MTG double bass pizzicato”** for guaranteed professional quality. **“cello sustained bow”**, **“violin bow sustained”**, **“pizzicato cello”**, **“double bass pizzicato”**, **“cello harmonics”**, **“violin harmonic”**, **“guitar harmonic sustained”**, **“classical guitar harmonics”**, **“vibraphone bow”**.

Critical tags: **“single-note”**, **“sustained”**, **“good-sounds”**, **“multisample”**, **“non-vibrato” or “no-vibrato”**, **“clean”**, **“resonance”**, **“neumann-U87”** (indicates professional recording).

Browse MTG user packs for systematic collections. Carlos_Vaquero offers high-quality viola and bass recordings (pack #9520 for Viola Tenuto with non-vibrato sustained notes D4-D5 range, though CC BY-NC).  Search for specific professional equipment: “Neumann U87”, “Rode NT4” in descriptions.

Look for descriptions specifying: **concert pitch (440Hz or 442Hz)**, **MIDI note numbers**, **“mono” channel** (cleaner for pitch-shifting than stereo), **professional microphones**, **academic/institutional sources** (MTG, university recordings), **24-bit depth**, **sample rate 44.1kHz or 48kHz**, **“clean articulation”**, **“sustained”**, **“single note”**.

### Quality criteria and common pitfalls

**Ideal characteristics**: Non-vibrato or slow/wide vibrato only (fast narrow vibrato creates frequency modulation becoming jarring when pitch-shifted), clean attack without bow scratches or grainy transients, 1-10 second sustain with natural decay, clear single pitch (not sympathetic string resonance), monophonic recording preferred, minimal room sound (close-miked), 24-bit depth, 48kHz+ sample rate. Cello F2 and double bass samples ideal for grounding low registers, violin C4 and guitar harmonics for ethereal high registers.

**Critical pitfalls**: Vibrato issues—fast narrow vibrato (6-8Hz rate) with rapid pitch wobble destroys pitch-shifting (seek “non-vibrato” tags or slow 2-3Hz wide vibrato). Bow scratches and attack noise—harsh transients in first 50-200ms from initial bow contact (look for samples “after bow is lifted” like ID 156664 or with clean attacks). Fret/finger noise—squeaks and slides on guitar/bass (harmonics avoid this—ID 183808 pack). Overly short plucks—pizzicato under 0.8s lacks sufficient sustain (MTG double bass pizzicato samples provide 3-3.5 seconds). Room reflections and reverb—baked-in room sound limits processing options and muddies shifting (prefer academic recordings from MTG in controlled environments). Multiple string sympathetic resonance—other strings resonating creates complex harmonics shifting unpredictably. Digital artifacts—low bitrate, compression, clipping (use 24-bit/48kHz sources when available). Inconsistent tuning—samples not at concert pitch harder to shift consistently (MTG specifies 442Hz or 440Hz reference).

Avoid tags: “melody”, “phrase”, “song”, “vibrato” (unless specified as slow/wide), “tremolo”, “trill”, “fx”, “processed”, “reverb”. Watch for duration under 0.5 seconds for bowed sounds, multiple instruments playing together, lo-fi or compressed recordings.

## Technical evaluation: How to judge pitch-shifting suitability

Pitch-shifting quality depends on harmonic structure, temporal characteristics, and recording fidelity. **Simple harmonic content with clear fundamental frequency shifts cleanest**—this explains why sine waves, tubular bells, and non-vibrato strings outperform complex textures. Understanding these principles enables quick evaluation before downloading.

### Harmonic content and spectral characteristics

**Ideal harmonic structure**: Clear fundamental frequency as dominant component (visible as strongest frequency band in spectrogram), moderate overtones in harmonic series (2x, 3x, 4x fundamental frequency creating musical richness), stable frequency content throughout sustain (no wobble or drift). **Best performers**: singing bowls, tubular bells, kalimba, crotales with rich but ordered harmonics; pure sine waves and triangle waves with minimal overtones; non-vibrato strings with clear fundamentals; clean analog synthesis (Modular Samples collections); guitar harmonics with sine-like purity.

**Problematic characteristics**: Dense inharmonic partials (metal crash cymbals, complex bells with many non-musical frequencies create dissonance when transposed), noise-based sounds without clear pitch (pure wind, static, breath without tonal component), frequency modulation (vibrato, LFO, chorus effects cause pitch instability—6-8Hz vibrato rate particularly problematic), narrow-band sounds (lacking overtones don’t shift musically—need some harmonic complexity).

Test by pitch-shifting ±12 semitones (one octave each direction) and listening for: artifacts or distortion, unclear pitch or “muddy” quality, unmusical dissonance, wobbling or beating, loss of character. Singing bowls and analog synth pads typically remain clean across ±12 semitones; complex processed sounds show artifacts beyond ±5 semitones.

### Temporal and envelope characteristics

**Optimal envelope for 50-80 BPM heartbeat timing**: At 60 BPM, triggers occur every 1 second. At 50 BPM, every 1.2 seconds. At 80 BPM, every 0.75 seconds. **Ideal sample duration: 0.8-2 seconds natural sustain** allows sound to nearly complete before next trigger at 60 BPM, creates gentle overlapping at 80 BPM for meditative layering, provides breathing room without gaps at 50 BPM.

**Attack phase considerations**: Fast clean attack (under 0.05 seconds) provides rhythmic precision for heartbeat synchronization—percussive but not harsh. Soft attack (0.05-0.15 seconds) creates smoother meditative quality—pads and bowed strings. Avoid very slow attacks over 0.2 seconds that mask heartbeat timing. Strong transient important for rhythmic definition but shouldn’t be harsh or clicky.

**Sustain and decay characteristics**: Natural exponential decay most musical (singing bowls, bells, kalimba)—gradual volume reduction feels organic. Sustained plateau with slow decay works for ambient pads—can crossfade or gate as needed. Avoid abrupt cuts or artificial fade-outs limiting flexibility. Longer sustains (3-10+ seconds) from crystal bowls, gongs, and ambient drones provide flexibility for slower tempos and can be trimmed.

**Pitch-shifting effects on duration**: Shifting down lengthens samples—sample at 1 second becomes 1.26 seconds when shifted down 5 semitones. Shifting up shortens duration—1 second becomes 0.84 seconds when shifted up 3 semitones. Plan accordingly: for lower pitches, start with shorter samples or higher-pitched sources; for higher pitches, ensure longer original samples to maintain sustain.

### Recording quality indicators

**Format and bit depth requirements**: WAV or FLAC uncompressed formats essential—MP3/OGG compression artifacts amplify during pitch-shifting. 24-bit depth preferred over 16-bit for 48dB additional dynamic range and headroom for processing. 16-bit acceptable if clean recording. Sample rate 44.1kHz minimum (CD quality), 48kHz standard for production, 96kHz or 192kHz ideal for extreme transposition ±12+ semitones preserving more harmonics.

**Microphone and recording technique**: Professional equipment indicates quality intent—Neumann U87, Rode NT series, Zoom H4n/H6, Audio-Technica, Sennheiser. Close-miking reduces room sound for cleaner pitch-shifting—look for “close mic” in descriptions. Minimal room reflections and reverb (you can add later)—avoid “cathedral”, “hall”, processed reverb. Low noise floor (professional recorders and quiet environment)—electrical hum, HVAC noise, traffic amplify when pitched down. No clipping or distortion (check waveforms for flat peaks)—digital clipping cannot be removed.

**Community validation signals**: High ratings (4+ stars with multiple votes), many downloads (popular samples community-vetted), positive comments (“clean”, “professional”, “clear”, “perfect”), detailed descriptions with technical specs, organized packs from systematic recording sessions, academic institutional sources (MTG samples consistently excellent).

### Sample length recommendations by timbral family

**Metallic/bell-like**: 1-10 seconds ideal (singing bowls and crystal bowls sustain longest, hand bells shorter at 0.8-1.5 seconds, tubular bells 1.5-3 seconds, gongs 2-8 seconds). Long sustains provide flexibility for all tempos—trim if needed for faster sequences.

**Wooden percussion**: 0.8-4 seconds optimal (kalimba 1.5-4 seconds best, marimba 1.5-3 seconds, xylophone 1-4 seconds depending on bar size, tongue drums 2-5 seconds, wood blocks 0.3-0.8 seconds for percussive accents). Shorter sustains suit faster heartbeat rates.

**Synth tones**: 1-10+ seconds highly flexible (pads and drones 5-20+ seconds can be looped or trimmed, plucks 1-3 seconds, ambient tones variable, simple waveforms 2-5 seconds sufficient). Digital nature allows easy looping for infinite sustain if needed.

**Natural/organic**: 0.5-2 seconds typical (water drops 0.5-1.5 seconds, stone/wood impacts 0.5-1.5 seconds, bell-like organic sounds 2-10 seconds, breath sounds 1-3 seconds). Shorter organic sounds work for accents and rhythmic punctuation.

**String resonance**: 2-10+ seconds excellent (bowed strings 3-10 seconds depending on bow length, pizzicato 2-4 seconds, harmonics 3-6 seconds with pure decay, vibraphone bow 5-10+ seconds for sustained tones). Longer sustains essential for meditative quality.

## Sample library organization and workflow strategy

Efficient organization enables quick access during installation programming and future updates. **Structure your library hierarchically by timbral family, then by pitch range, with clear naming conventions encoding essential metadata**. This system scales from initial 80-sample library to expanded 200+ sample collections.

### Folder structure recommendation

```
Heartbeat_Sample_Library/
├── 01_Metallic_Bells/
│   ├── A_Singing_Bowls/
│   │   ├── LOW_SingingBowl_C2_122650_CC-BY.wav
│   │   ├── MID_SingingBowl_D4_439235_CC0.wav
│   │   └── HIGH_CrystalBowl_G5_129219_CC-BY.wav
│   ├── B_Tubular_Bells/
│   │   └── MID_TubularBell_C4_374273_CC0.wav
│   ├── C_Gongs/
│   │   └── LOW_Gong_A1_86773_CC-BY.wav
│   └── D_Hand_Bells/
│       └── HIGH_HandBell_G5_339818_CC-BY.wav
├── 02_Wooden_Percussion/
│   ├── A_Kalimba/
│   │   ├── LOW_Kalimba_C3_58715_Sampling.wav
│   │   └── MID_Kalimba_C4_331047_CC0.wav
│   ├── B_Marimba/
│   │   ├── MID_Marimba_G4_255689_CC-BY.wav
│   │   └── HIGH_Marimba_C7_255681_CC-BY.wav
│   ├── C_Xylophone/
│   │   └── MID_Xylophone_C5_232002_CC-BY.wav
│   └── D_Tongue_Drums/
│       └── MID_TongueDrum_Extract_381955_CC0.wav
├── 03_Synth_Tones/
│   ├── A_Analog_Bass/
│   │   └── LOW_KorgMonoPoly_C2_295334_CC0.wav
│   ├── B_Ambient_Pads/
│   │   ├── MID_PPG_Organwave_D4_6251_CC-BY.wav
│   │   └── LOW_SpaceDrone_C2_46098_CC-BY.wav
│   ├── C_Plucks/
│   │   └── MID_KorgZ1_Pluck_C4_pack17413_CC0.wav
│   └── D_Pure_Tones/
│       └── MID_SineWave_A4_8795_CC-BY.wav
├── 04_Natural_Organic/
│   ├── A_Water/
│   │   └── HIGH_WaterDrop_536113_CC-BY.wav
│   ├── B_Metal_Organic/
│   │   ├── MID_Crotales_D4_219633_CC0.wav
│   │   └── MID_MeditationBell_42095_CC0.wav
│   ├── C_Bamboo_Wood/
│   │   └── MID_Bamboo_Hit_386888_CC0.wav
│   └── D_Stone/
│       └── LOW_RockWood_319226_CC0.wav
└── 05_String_Resonance/
    ├── A_Cello/
    │   ├── LOW_Cello_C2_Resonance_156664_CC-BY.wav
    │   ├── LOW_Cello_F2_357907_CC-BY.wav
    │   └── MID_Cello_C4_358232_CC-BY.wav
    ├── B_Violin/
    │   └── MID_Violin_C4_356134_CC-BY.wav
    ├── C_Pizzicato/
    │   ├── LOW_DoubleBass_A1_Pizz_354309_CC-BY.wav
    │   └── LOW_DoubleBass_D2_Pizz_354314_CC-BY.wav
    ├── D_Harmonics/
    │   └── MID_Guitar_Harmonic_G4_183808_CC0.wav
    └── E_Alternative/
        └── HIGH_Vibraphone_Bow_254349_CC0.wav
```

### Naming convention encoding metadata

**Format**: `[RANGE]_[INSTRUMENT]_[PITCH]_[ID]_[LICENSE].wav`

**Range prefix** (LOW/MID/HIGH) indicates register for quick selection: LOW (fundamental C0-C3, grounding bass tones), MID (C3-C5, primary melodic range), HIGH (C5-C8, ethereal bright tones). This enables instant identification without listening.

**Instrument name** describes source concisely (SingingBowl, Kalimba, KorgMonoPoly, WaterDrop, Cello). Avoid overly long names—abbreviate if needed while maintaining clarity.

**Pitch notation** when available (C2, D4, G5, A4) or approximate pitch enables harmonic framework planning. If extracting from longer recordings, note “Extract” or approximate pitch from analysis.

**Freesound ID** (122650, 331047, etc.) enables tracking back to source for licensing, re-downloading higher quality, finding related samples from same user or pack.

**License abbreviation** (CC0, CC-BY, CC-BY-NC, Sampling) ensures proper attribution tracking and identifies public domain samples for maximum flexibility.

### How many samples per timbral family

**Minimum viable library (60-80 samples total)**: Metallic/bells 15-20 samples (5 singing bowls spanning LOW-HIGH range, 3-5 tubular bells, 2-3 gongs, 3-5 hand bells or chimes), Wooden percussion 12-15 samples (4-5 kalimba, 3-4 marimba, 3-4 xylophone, 1-2 tongue drums), Synth tones 15-20 samples (3-5 analog bass, 4-6 ambient pads, 3-4 plucks, 2-3 pure tones), Natural/organic 8-12 samples (2-3 water, 3-4 metal organic like crotales/bells, 2-3 bamboo/wood, 1-2 stone), String resonance 10-15 samples (3-4 cello, 1-2 violin, 2-3 pizzicato, 2-3 harmonics, 1-2 alternative like vibraphone bow).

**Expanded professional library (120-150 samples)**: Double quantities above focusing on: MORE pitch variety within each instrument (chromatic or pentatonic coverage), velocity layers (soft/medium/loud versions), timbral variations (different singing bowl materials, multiple kalimba tunings), special techniques (harmonics, prepared sounds, extended techniques), alternative sources adding textural variety.

**Massive installation library (200+ samples)**: Triple minimum quantities with: Complete chromatic coverage C2-C6 in primary instruments, multiple round-robin samples (3-5 versions of same pitch for variation avoiding repetition), seasonal or thematic variations, processed variations (light reverb versions, filtered versions) while maintaining clean originals, regional variations (Tibetan vs. crystal singing bowls, African vs. modern kalimba).

### Quality control and testing workflow

**Phase 1 - Initial download and organization** (first session): Download 10-15 samples per timbral family based on research, rename immediately using naming convention, organize into folder structure, create spreadsheet tracking: Freesound ID, filename, license type, attribution text, original pitch if known, duration, bit depth/sample rate, date downloaded, any processing notes.

**Phase 2 - Technical testing** (dedicated session): Import all samples into DAW at consistent project sample rate (48kHz recommended). Normalize to -3dB for consistent levels. Trim silence from start (leave clean attack) and excessive tail (keep natural decay, remove pure silence). Check spectral analysis for: clear fundamental frequency, harmonic content appropriateness, noise floor issues, frequency range coverage. Test pitch-shifting: ±12 semitones (one octave range), ±7 semitones (perfect fifth range—most common need), listen for artifacts, unclear pitch, unmusical dissonance. Rate each sample: 5 stars (perfect, use prominently), 4 stars (very good, standard use), 3 stars (acceptable, secondary use), 2 stars or below (replace or use sparingly).

**Phase 3 - Musical testing** (creative session): Create test sequence at 60 BPM (one hit per second) with samples from each family. Test polyrhythmic layering—4 different samples at slightly different tempos simulating participant variation. Experiment with pitch-shifted harmonic collections: pentatonic scale (5 notes: C, D, E, G, A), minor scale (7 notes: C, D, Eb, F, G, Ab, Bb), major scale (7 notes: C, D, E, F, G, A, B), custom meditative scales. Listen for: Overall timbral balance across families, samples that dominate or disappear, combinations creating mud or harshness, samples providing clarity or grounding. Refine selection based on musical context.

**Phase 4 - Documentation and attribution**: Create CREDITS.txt file listing all samples with required attribution: Freesound ID and title, username/creator, source URL, license type. Example entry: “Singing bowl.wav (ID: 122650) by juskiddink, freesound.org/people/juskiddink/sounds/122650/, CC BY 3.0”. Create README.txt documenting: Folder structure, naming convention, pitch-shifting recommendations per sample, suggested harmonic frameworks, installation notes. For CC0 samples, attribution optional but considerate—simple list suffices.

### Backup and version control

**Maintain three versions**: Raw originals (unprocessed downloads with original names in ARCHIVE folder—never modify these), Processed samples (trimmed, normalized, renamed in main library folders—working versions), Pitch-shifted collections (pre-rendered harmonic sets if installation uses fixed scales rather than real-time shifting). Use cloud backup (Google Drive, Dropbox) for disaster recovery. Version control critical if multiple people access library—date-stamp major updates (Heartbeat_Library_v1.0_2025-11-13).

## Conclusion: Building your versatile pitch-shifting library efficiently

The path to an exceptional heartbeat installation sample library starts with **understanding freesound.org’s systematic collections over random searching**. The MTG Good-sounds database, sgossner’s VSCO 2 CE orchestral project, modularsamples’ 40,000-sample analog synth library, and juskiddink’s professional instrument recordings provide consistent quality eliminating hours of trial-and-error. These academic and professional contributors document technical specifications, use standardized recording techniques, and typically offer CC0 or CC Attribution licensing enabling immediate use.

**Prioritize non-vibrato sustained tones with clear fundamentals and simple-to-moderate harmonic complexity**—this single principle separates samples that pitch-shift cleanly from those creating artifacts. Singing bowls, tubular bells, non-vibrato cello, pure sine waves, and analog synth bass exemplify ideal characteristics. Avoid built-in modulation, heavy processing, complex inharmonic partials, and insufficient sustain. The 0.8-2 second sweet spot for sample duration maps perfectly to 50-80 BPM heartbeat timing, though longer sustains provide flexibility for slower tempos and meditative overlapping.

Start your library with the essential 12 samples from each timbral family identified in this guide—60 samples total providing comprehensive timbral coverage. Test pitch-shifting across ±12 semitones before expanding. Organize hierarchically with metadata-rich naming conventions enabling rapid access during installation programming. As your library grows to 120-150 samples, focus on pitch variety within successful instruments rather than adding marginal timbral categories. The goal: versatile source material transforming through pitch-shifting into any harmonic framework your installation requires—pentatonic, minor, major, or custom meditative scales—while maintaining the organic, resonant quality essential for immersive heartbeat-synchronized art experiences.