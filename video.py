from google.cloud import videointelligence, translate_v2 as translate
from google.oauth2 import service_account
import io, os, cv2, math, pickle, pysubs2

service_account_file = "service_account.json"
path = r"C:\Users\plan2\Downloads\Test\เพื่อลูก\Downloads\3.mp4"
confidence = 0.2
timeout = 600
video_language = "th-TH" # th-TH
translatelanguage = "" # th
    
def get_max_confidence(text_annotation):
    max_confidence = 0
    for segment in text_annotation.segments:
        segment_confidence = segment.confidence
        if segment_confidence > max_confidence:
            max_confidence = segment_confidence
    return max_confidence

def get_video_resolution(video_path):
    video = cv2.VideoCapture(video_path)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video.release()
    return width, height

def get_video_duration(video_path):
    video = cv2.VideoCapture(video_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    video.release()
    return frame_count / fps

with io.open(path, "rb") as file:
    input_content = file.read()

video_basename = os.path.splitext(os.path.basename(path))[0]
subtitle_filename = f"{video_basename}.ass"
pickle_file_name = f"backup-{video_basename}.pickle"
subtitle_full_path = os.path.join(os.path.dirname(path), subtitle_filename)
pickle_full_path = os.path.join(os.path.dirname(path), pickle_file_name)

video_duration = get_video_duration(path)
segment_duration = 60
total_segments = math.ceil(video_duration / segment_duration)
video_width, video_height = get_video_resolution(path)

credentials = service_account.Credentials.from_service_account_file(
    service_account_file)
video_client = videointelligence.VideoIntelligenceServiceClient(
    credentials=credentials)
translation_client = translate.Client(
    credentials=credentials)

features = [
    videointelligence.Feature.TEXT_DETECTION
]

video_context = videointelligence.VideoContext(
    **({"text_detection_config": videointelligence.TextDetectionConfig(language_hints=[video_language])} if video_language else {}),
)


if os.path.exists(pickle_full_path):
    print("\nLoad Backup to Processing Text: ", pickle_full_path)
    with open(pickle_full_path, "rb") as file:
        result = pickle.load(file)
else:
    print("\nProcessing video: ", path)

    operation = video_client.annotate_video(
        request={
            "features": features,
            "input_content": input_content,
            # "video_context": video_context
        }
    )

    result = operation.result(timeout=timeout)

    print("\nBackup Processing to: ", pickle_full_path)
    with open(pickle_full_path, "wb") as file:
        pickle.dump(result, file)


subs = pysubs2.SSAFile()

text_annotations_with_confidence = []

for annotation_result in result.annotation_results:
    for text_annotation in annotation_result.text_annotations:
        # max_confidence = get_max_confidence(text_annotation)
        # if max_confidence >= confidence:
            if translatelanguage:
                translation = translation_client.translate(text_annotation.text, target_language=translatelanguage)
                text = translation['translatedText']
            else:
                text = text_annotation.text
            text_annotations_with_confidence.append((text_annotation, text))

for text_annotation, text in text_annotations_with_confidence:
    for segment in text_annotation.segments:
        start_time_offset = segment.segment.start_time_offset
        end_time_offset = segment.segment.end_time_offset
        start_seconds = start_time_offset.total_seconds()
        end_seconds = end_time_offset.total_seconds()

        frames = segment.frames
        if frames:
            frame = frames[0]
            vertices = frame.rotated_bounding_box.vertices

            x = int(sum(vertex.x for vertex in vertices) / len(vertices) * video_width)
            y = int(sum(vertex.y for vertex in vertices) / len(vertices) * video_height) + 35

            formatted_text = f"{{\\pos({x},{y})}}{text}"
            subs.append(pysubs2.SSAEvent(
                start=pysubs2.make_time(s=start_seconds),
                end=pysubs2.make_time(s=end_seconds),
                text=formatted_text,
            ))
            # if y >= video_height // 2:
            #     formatted_text = f"{{\\pos({x},{y})}}{text}"
            #     subs.append(pysubs2.SSAEvent(
            #         start=pysubs2.make_time(s=start_seconds),
            #         end=pysubs2.make_time(s=end_seconds),
            #         text=formatted_text,
            #     ))               
sorted_events = sorted(subs, key=lambda x: x.start)
subs.clear()
subs.extend(sorted_events)

subs.save(subtitle_full_path)

print("\nfinnished processing.\n")