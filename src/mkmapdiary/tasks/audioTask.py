import hashlib
import logging
import threading
from collections.abc import Iterator
from pathlib import PosixPath
from typing import Any

from pydub import AudioSegment

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.util.log import ThisMayTakeAWhile

from .base.baseTask import BaseTask

whisper_lock = threading.Lock()

logger = logging.getLogger(__name__)


class AudioTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self.__sources: list[PosixPath] = []

    def handle_audio(self, source: PosixPath) -> Iterator[AssetRecord]:
        # Create task to convert image to target format
        self.__sources.append(source)

        timestamp = self.extract_meta_datetime(source)

        asset = AssetRecord(
            path=self.__generate_destination_filename(source, ".mp3"),
            type="audio",
            timestamp_utc=timestamp,
        )

        transcript_asset = AssetRecord(
            path=self.__generate_destination_filename(source, ".mp3.md"),
            type="transcript",
            timestamp_utc=timestamp,
        )

        yield asset
        yield transcript_asset

    def __generate_destination_filename(
        self, source: PosixPath, suffix: str
    ) -> PosixPath:
        filename = PosixPath(self.dirs.assets_dir / source.stem).with_suffix(suffix)
        return self.make_unique_filename(source, filename)

    def task_convert_audio(self) -> Iterator[dict[str, Any]]:
        """Convert an image to a different format."""

        def _convert(src: PosixPath, dst: PosixPath) -> None:
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

    def __file_md5(self, path: PosixPath) -> str:
        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def __transcribe_audio(self, src: PosixPath) -> dict[str, Any]:
        import whisper

        with whisper_lock:
            with ThisMayTakeAWhile(logger, f"Transcribing audio: {src.name}"):
                if not hasattr(self, "_model"):
                    # Loading the model seems to leak memory; therefore, we
                    # load it only once and reuse it.
                    self._model = whisper.load_model("turbo")
                result = self._model.transcribe(str(src))
        return result

    def task_transcribe_audio(self) -> Iterator[dict[str, Any]]:
        """Transcribe audio to text."""

        def _transcribe(src: PosixPath, dst: PosixPath) -> None:
            audio_title = self.config["strings"]["audio_title"]

            if not self.config["features"]["transcription"]["enabled"]:
                with open(dst, "w") as f:
                    f.write(f"### {audio_title}\n\n")
                return

            output = []
            output.append("<div class='transcript'>")

            if self.config["features"]["transcription"]["user_cache"]:
                result = self.with_cache(
                    "whisper",
                    self.__transcribe_audio,
                    src,
                    cache_args=(self.__file_md5(src),),
                )
            else:
                result = self.__transcribe_audio(src)

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
                    ),
                )
                text.append(segment["text"].strip())

            title = self.ai(
                "generate_title",
                dict(locale=self.config["site"]["locale"], text=text),
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
