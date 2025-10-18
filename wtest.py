src = "/home/janna/projekte/travel-diary/build/docs/assets/2025-08-25-02-48-40.mp3"

model = whisper.load_model("turbo")
audio = AudioSegment.from_file(src)

result = model.transcribe(src)

for segment in result["segments"]:
    if segment["end"] > audio.duration_seconds:
        break

    print(f"[{segment['start']:.2f}s]: {segment['text']}")
