#!/bin/bash
# Procedural sound-effect kit (no licences needed). Re-run to regenerate. All -> 48 kHz stereo mp3.
set -e; cd "$(dirname "$0")"
F="ffmpeg -v error -y"
# whoosh: pink noise through a sweeping band-pass, swelling in and out (0.7 s)
$F -f lavfi -i "anoisesrc=d=0.7:c=pink:a=0.9" -af "bandpass=f=900:w=1.4,volume='sin(PI*t/0.7)^2':eval=frame,afade=t=out:st=0.55:d=0.15,highpass=f=180,loudnorm=I=-20:TP=-3" -ac 2 -ar 48000 whoosh.mp3
# whoosh_long: slower, darker (1.2 s)
$F -f lavfi -i "anoisesrc=d=1.2:c=brown:a=0.9" -af "lowpass=f=2500,highpass=f=120,volume='sin(PI*t/1.2)^3':eval=frame,loudnorm=I=-21:TP=-3" -ac 2 -ar 48000 whoosh_long.mp3
# tick: tiny click for counters (40 ms)
$F -f lavfi -i "aevalsrc='0.8*sin(2*PI*2200*t)*exp(-90*t)':d=0.04" -af "loudnorm=I=-22:TP=-3" -ac 2 -ar 48000 tick.mp3
# pop: soft UI pop for text/list items (120 ms, downward pitch)
$F -f lavfi -i "aevalsrc='0.9*sin(2*PI*(700-2500*t)*t)*exp(-28*t)':d=0.12" -af "loudnorm=I=-20:TP=-3" -ac 2 -ar 48000 pop.mp3
# riser: rising tone + noise swell into a reveal (1.6 s)
$F -f lavfi -i "aevalsrc='0.35*sin(2*PI*(180*t+140*t*t)*1)*(t/1.6)^2|0.35*sin(2*PI*(181*t+141*t*t))*(t/1.6)^2':d=1.6" -f lavfi -i "anoisesrc=d=1.6:c=pink:a=0.25" -filter_complex "[1]highpass=f=1500,volume='(t/1.6)^3':eval=frame[n];[0][n]amix=inputs=2:normalize=0,afade=t=out:st=1.5:d=0.1,loudnorm=I=-21:TP=-3" -ac 2 -ar 48000 riser.mp3
# impact: low cinematic boom for big reveals (1.8 s)
$F -f lavfi -i "aevalsrc='0.9*sin(2*PI*(55-20*t)*t)*exp(-2.2*t)+0.3*sin(2*PI*110*t)*exp(-6*t)':d=1.8" -f lavfi -i "anoisesrc=d=0.25:c=brown:a=0.6" -filter_complex "[1]lowpass=f=400,afade=t=out:d=0.25[n];[0][n]amix=inputs=2:normalize=0,loudnorm=I=-18:TP=-2" -ac 2 -ar 48000 impact.mp3
# shutter: double click for photo/archive reveals (0.15 s)
$F -f lavfi -i "aevalsrc='(0.8*exp(-120*t)+0.6*exp(-120*(t-0.08))*gte(t,0.08))*(random(0)-0.5)':d=0.15" -af "highpass=f=1200,loudnorm=I=-22:TP=-3" -ac 2 -ar 48000 shutter.mp3
for f in *.mp3; do printf "%s %s\n" "$f" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 $f)"; done
