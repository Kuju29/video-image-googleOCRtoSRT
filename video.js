const videoIntelligence = require("@google-cloud/video-intelligence");
const fs = require("node:fs");

async function main() {
  try {
    console.log("Starting program now...");
    const client = new videoIntelligence.VideoIntelligenceServiceClient({
      keyFilename: "./service_account.json",
    });
    const file = fs.readFileSync("./1.mp4");
    const outputFile = "./video.srt";

    if (!fs.existsSync(outputFile)) {
      fs.writeFileSync(outputFile, "");
      console.log("Create SRT files");
    }

    const transcriptConfig = {
      languageCode: "th-TH",
      enableWordTimeOffsets: true,
    };
    const languageHints = ["th-TH"];
    const location = {
      left: 0.2,
      top: 0.7,
      right: 0.8,
      bottom: 0.9,
    };
    const videoContext = {
      speechTranscriptionConfig: transcriptConfig,
      languageHints: languageHints,
      location: location,
    };

    const request = {
      inputContent: file,
      features: ["TEXT_DETECTION"],
      videoContext: videoContext,
    };

    const [operation] = await client.annotateVideo(request);
    console.log("Converting data...");
    const [annotations] = await operation.promise();
    const srt = annotations.annotationResults[0].textAnnotations
      .map((annotation, i) => {
        const { text, segments } = annotation;
        if (!segments) return "";
        return segments.map((segment, j) => {
          const { startTime, endTime } = segment;
          const startSrt = toSrtTime(startTime);
          const endSrt = toSrtTime(endTime);
          return `${startSrt} --> ${endSrt}\n${text}\n`;
        });
      })
      .flat()
      .join("");
    fs.writeFileSync(outputFile, srt);
    console.log("Done!!!");
  } catch (error) {
    console.log(error);
  }
}

function toSrtTime(duration) {
  const timeInSeconds = duration && duration.seconds + duration.nanos / 1e9;
  if (isNaN(timeInSeconds) || timeInSeconds === undefined) {
    // console.log(`Invalid value for timeInSeconds: ${timeInSeconds}`);
    return "00:00:00,000";
  }
  const date = new Date(timeInSeconds * 1000);
  const hours = pad(date.getUTCHours(), 2);
  const minutes = pad(date.getUTCMinutes(), 2);
  const seconds = pad(date.getUTCSeconds(), 2);
  const milliseconds = pad(date.getUTCMilliseconds(), 3);

  return `${hours}:${minutes}:${seconds},${milliseconds}`;
}

function pad(n, width) {
  n = n + "";
  return n.length >= width ? n : new Array(width - n.length + 1).join("0") + n;
}

main();
