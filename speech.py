import io, os, sys, pysrt, datetime
from moviepy.editor import *
from google.cloud import speech_v1p1beta1 as speech
from pydub import AudioSegment
from tqdm import tqdm

language_video = "ko-KR"  # "en-US", "th-TH", "ko-KR", "ja-JP"

def extract_audio_from_video(input_file, output_file):
    video = VideoFileClip(input_file)
    audio = video.audio
    audio.write_audiofile(output_file)

def timedelta_to_srttime(time_delta):
    total_seconds = int(time_delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(time_delta.microseconds / 1000)
    return pysrt.SubRipTime(hours, minutes, seconds, milliseconds)

def transcribe_audio_with_timing(audio_file, chunk_size=3000):
    client = speech.SpeechClient.from_service_account_file(
        'service_account.json'
    )

    audio = AudioSegment.from_file(audio_file)
    audio.export("temp_audio.wav", format="wav")
    audio_mono = AudioSegment.from_file("temp_audio.wav").set_channels(1)

    chunks = [audio_mono[i:i + chunk_size] for i in range(0, len(audio_mono), chunk_size)]

    subtitles = []
    accumulated_time = datetime.timedelta()

    for chunk in tqdm(chunks, desc="Processing audio chunks", unit="chunk"):
        with io.BytesIO() as wav_file:
            chunk.export(wav_file, format="wav")
            content = wav_file.getvalue()

        recognition_audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=44100,
            enable_word_time_offsets=True,
            language_code=language_video,
        )

        operation = client.long_running_recognize(config=config, audio=recognition_audio)
        response = operation.result()

        for result in response.results:
            alternative = result.alternatives[0]
            start_time = alternative.words[0].start_time + accumulated_time
            end_time = alternative.words[-1].end_time + accumulated_time
            subtitle = pysrt.SubRipItem(
                start=timedelta_to_srttime(start_time),
                end=timedelta_to_srttime(end_time),
                text=alternative.transcript
            )
            subtitles.append(subtitle)

        accumulated_time += datetime.timedelta(milliseconds=chunk.duration_seconds * 1000)

    return subtitles

def convert_to_srt(subtitles, output_file):
    srt_file = pysrt.SubRipFile()
    for subtitle in subtitles:
        srt_file.append(subtitle)
    srt_file.save(output_file, encoding='utf-8')

def main(input_file):
    print("Starting script...")

    if not os.path.isfile(input_file):
        print(f"File not found: {input_file}")
        sys.exit(1)

    temp_audio_file = "temp_audio.wav"

    if input_file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm')):
        print("Extracting audio from video...")
        extract_audio_from_video(input_file, temp_audio_file)
    elif input_file.lower().endswith(('.mp3', '.wav', '.ogg', '.flac')):
        temp_audio_file = input_file
    else:
        print("Unsupported file format. Please provide a video or audio file.")
        sys.exit(1)

    print("Transcribing audio and generating subtitles...")
    subtitles = transcribe_audio_with_timing(temp_audio_file)

    if temp_audio_file != input_file:
        os.remove(temp_audio_file)

    file_name_without_extension = os.path.splitext(input_file)[0]
    output_file = f"{file_name_without_extension}.srt"
    print("Converting subtitles to SRT format...")
    convert_to_srt(subtitles, output_file)

    print("Output .srt file done!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python srt.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    main(input_file)
