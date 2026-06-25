import librosa 
y, sr = librosa.load(r"D:\Lil Tecca - Don't Rush (Official Visualizer)_TC_raw_audio.wav") 
print("librosa.load OK", sr, len(y)) 
