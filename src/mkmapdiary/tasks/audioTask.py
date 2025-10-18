from PIL import Image
from .base.baseTask import BaseTask
from .base.exifReader import ExifReader
from pydub import AudioSegment
import hashlib
from pathlib import PosixPath
from typing import Callable, Dict, Iterator, List, Tuple, Union, Any


class AudioTask(BaseTask):
    def __init__(self):
        super().__init__()
        self.__sources = []

    def handle_audio(self, source):
        # Create task to convert image to target format
        self.__sources.append(source)

        meta = {
            "date": self.extract_meta_datetime(source),
        }

        yield self.Asset(
            self.__generate_destination_filename(source, ".mp3"), "audio", meta
        )
        yield self.Asset(
            self.__generate_destination_filename(source, ".mp3.md"), "transcript", meta
        )

    def __generate_destination_filename(self, source, suffix):
        filename = (self.assets_dir / source.stem).with_suffix(suffix)
        return self.make_unique_filename(source, filename)

    def task_convert_audio(self) -> Iterator[Dict[str, Any]]:
        """Convert an image to a different format."""

        def _convert(src, dst):
            audio = AudioSegment.from_file(src)
            audio.export(dst, format="mp3")

        for src in self.__sources:
            dst = self.__generate_destination_filename(src, ".mp3")
            yield dict(
                name=dst,
                actions=[(_convert, (src, dst))],
                file_dep=[src],
                task_dep=[f"create_directory:{dst.parent}"],
                targets=[dst],
            )

    def __file_md5(self, path):
        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def __transcribe_audio(self, src):
        import whisper

        model = whisper.load_model("turbo")
        result = model.transcribe(str(src))
        return result

    def task_transcribe_audio(self) -> Iterator[Dict[str, Any]]:
        """Transcribe audio to text."""

        def _transcribe(src, dst):

            audio_title = self.config["audio_title"]

            if not self.config["features"]["transcription"]:
                with open(dst, "w") as f:
                    f.write(f"### {audio_title}\n\n")
                return

            output = []
            output.append("<div class='transcript'>")

            result = self.with_cache(
                "whisper",
                self.__transcribe_audio,
                src,
                cache_args=(self.__file_md5(src),),
            )

            audio = AudioSegment.from_file(src)
            text = []

            for segment in result["segments"]:
                if segment["end"] > audio.duration_seconds:
                    break

                output.append(
                    self.template(
                        "transcript_segment.j2",
                        start=int(segment["start"]),
                        end=int(segment["end"]),
                        text=segment["text"].strip(),
                    )
                )
                text.append(segment["text"].strip())

            title = self.ai(
                "generate_title", format=dict(locale=self.config["locale"], text=text)
            )

            output.append("</div>")

            with open(dst, "w") as f:
                f.write(f"### {audio_title}: {title}\n\n")
                f.write("\n".join(output))

        for src in self.__sources:
            dst = self.__generate_destination_filename(src, ".mp3.md")
            yield dict(
                name=dst,
                actions=[(_transcribe, (src, dst))],
                file_dep=[src],
                task_dep=[f"create_directory:{dst.parent}"],
                targets=[dst],
            )
