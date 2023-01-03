const vision = require("@google-cloud/vision");
const fs = require("node:fs");

async function main() {
  try {
    console.log("Starting program now...");
    const client = new vision.ImageAnnotatorClient({
      keyFilename: "./service_account.json",
    });
    const folderPath =
      "./VideoSubFinder_5.60_x64/Release_x64/RGBImages";
    const outputFile = "./image.srt";

    if (!fs.existsSync(outputFile)) {
      fs.writeFileSync(outputFile, "");
      console.log("Create SRT files");
    }

    const filenames = await fs.promises.readdir(folderPath);
    const imageContents = await Promise.all(
      filenames.map((filename) =>
        fs.promises.readFile(`${folderPath}/${filename}`)
      )
    );

    const imageBuffers = imageContents.map((content) =>
      new Buffer.from(content, "base64")
    );

    const detections = await Promise.all(
      imageBuffers.map((buffer) =>
        client.textDetection({
          image: buffer,
          languageHints: ["th-TH"],
          min_score: 0.5,
          max_results: 1,
        })
      )
    );
    
    const texts = detections.map((detection) => detection[0].textAnnotations[0]?.description || ""); 
    const times = filenames.map((filename) => {
      const start_hour = filename.split('_')[0].slice(0, 2);
      const start_min = filename.split('_')[1].slice(0, 2);
      const start_sec = filename.split('_')[2].slice(0, 2);
      const start_micro = filename.split('_')[3].slice(0, 3);
      
      const end_hour = filename.split('__')[1].split('_')[0].slice(0, 2);
      const end_min = filename.split('__')[1].split('_')[1].slice(0, 2);
      const end_sec = filename.split('__')[1].split('_')[2].slice(0, 2);
      const end_micro = filename.split('__')[1].split('_')[3].slice(0, 3);
      
      return {
        start: `${start_hour}:${start_min}:${start_sec},${start_micro}`,
        end: `${end_hour}:${end_min}:${end_sec},${end_micro}`,
      };
    });
    
    let srt = "";
    for (let i = 0; i < texts.length; i++) {
      srt += `${i + 1}\n`; 
      srt += `${times[i].start} --> ${times[i].end}\n`; 
      srt += `${texts[i]}\n\n`;
    }
    fs.writeFileSync(outputFile, srt);
    

    console.log("Done!!");
  } catch (error) {
    console.log(error);
  }
}

main();
