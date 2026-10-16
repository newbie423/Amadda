from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, BinaryIO

import ocrmypdf
import pymupdf
from dotenv import load_dotenv
from google import genai

load_dotenv()

class LectureMaterialTextExtracter:
    def __init__(self):
        # Gemini 클라이언트는 실제 API 호출 시 생성합니다.
        self.__gemini_client = None

    def __read_pdf_bytes(
        self,
        source: bytes | bytearray | memoryview | BinaryIO,
    ) -> bytes:
        """PDF 입력을 bytes로 변환한다."""

        if isinstance(source, bytes):
            return source

        if isinstance(source, (bytearray, memoryview)):
            return bytes(source)

        if hasattr(source, "read"):
            data = source.read()

            if not isinstance(data, bytes):
                raise TypeError(
                    "PDF 스트림은 바이너리 데이터를 반환해야 합니다."
                )

            return data

        raise TypeError(
            "입력은 bytes, bytearray, memoryview 또는 "
            "바이너리 파일 유사 객체여야 합니다."
        )

    def __read_media_bytes(
        self,
        source: bytes | bytearray | memoryview | BinaryIO,
    ) -> bytes:
        """미디어 입력을 bytes로 변환한다."""

        if isinstance(source, bytes):
            return source

        if isinstance(source, (bytearray, memoryview)):
            return bytes(source)

        if hasattr(source, "read"):
            data = source.read()

            if not isinstance(data, bytes):
                raise TypeError(
                    "미디어 스트림은 바이너리 데이터를 반환해야 합니다."
                )

            return data

        raise TypeError(
            "입력은 bytes, bytearray, memoryview 또는 "
            "바이너리 파일 유사 객체여야 합니다."
        )

    def extract_text_from_pdf(
        self,
        pdf_lecture_material: (
            bytes | bytearray | memoryview | BinaryIO
        ),
        force_ocr: bool = False,
    ) -> dict[str, Any]:
        """PDF 강의 자료에서 페이지별 텍스트를 추출한다."""

        pdf_bytes = self.__read_pdf_bytes(pdf_lecture_material)

        if not pdf_bytes:
            raise ValueError("PDF 데이터가 비어 있습니다.")

        if b"%PDF-" not in pdf_bytes[:1024]:
            raise ValueError("올바른 PDF 데이터가 아닙니다.")

        with TemporaryDirectory(prefix="lecture_pdf_") as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.pdf"
            output_path = temp_path / "searchable.pdf"

            input_path.write_bytes(pdf_bytes)

            ocr_options = {
                "language": "kor+eng",
                "progress_bar": False,
            }

            if force_ocr:
                ocr_options["force_ocr"] = True
            else:
                ocr_options["skip_text"] = True

            ocrmypdf.ocr(
                str(input_path),
                str(output_path),
                **ocr_options,
            )

            pages: list[dict[str, Any]] = []

            with pymupdf.open(str(output_path)) as document:
                for page_number, page in enumerate(document, start=1):
                    page_text = page.get_text("text").strip()

                    pages.append({
                        "page_number": page_number,
                        "text": page_text,
                    })

            full_text = "\n\n".join(
                f"[페이지 {page['page_number']}]\n{page['text']}"
                for page in pages
            )

            return {
                "full_text": full_text,
                "pages": pages,
                "page_count": len(pages),
            }

    def __get_gemini_client(self):
        """Gemini API 클라이언트를 최초 1회 생성한다."""

        if self.__gemini_client is None:
            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY 환경 변수를 설정해 주세요."
                )

            self.__gemini_client = genai.Client(api_key=api_key)

        return self.__gemini_client

    def __transcribe_cloud_media(
        self,
        media_bytes: bytes,
        filename: str,
        language: str | None = "ko",
    ) -> dict[str, Any]:
        """Gemini 클라우드 API를 사용해 음성을 텍스트로 변환한다."""

        if not media_bytes:
            raise ValueError("미디어 데이터가 비어 있습니다.")

        client = self.__get_gemini_client()

        with TemporaryDirectory(prefix="lecture_audio_") as temp_dir:
            input_path = Path(temp_dir) / filename
            input_path.write_bytes(media_bytes)

            # 로컬 파일을 Gemini Files API에 업로드한다.
            audio_file = client.files.upload(
                file=str(input_path)
            )

            # 전사 전용 모델로 음성을 텍스트로 변환한다.
            interaction = client.interactions.create(
                model="gemini-3.5-transcribe",
                input=[
                    {
                        "type": "audio",
                        "uri": audio_file.uri,
                        "mime_type": audio_file.mime_type,
                    }
                ],
            )

            full_text = interaction.output_text or ""

        return {
            "full_text": full_text,
            "segments": [],
            "language": language,
            "language_probability": None,
            "duration": None,
        }

    def extract_text_from_mp3(
        self,
        mp3_lecture_material: (
            bytes | bytearray | memoryview | BinaryIO
        ),
        language: str | None = "ko",
    ) -> dict[str, Any]:
        """MP3 파일을 Gemini API로 전사한다."""

        media_bytes = self.__read_media_bytes(
            mp3_lecture_material
        )

        return self.__transcribe_cloud_media(
            media_bytes=media_bytes,
            filename="lecture.mp3",
            language=language,
        )

    def extract_text_from_mp4(
        self,
        mp4_lecture_material: (
            bytes | bytearray | memoryview | BinaryIO
        ),
        language: str | None = "ko",
    ) -> dict[str, Any]:
        """MP4에서 음성을 추출하고 Gemini API로 전사한다."""

        import subprocess
        import imageio_ffmpeg

        mp4_bytes = self.__read_media_bytes(mp4_lecture_material)

        if not mp4_bytes:
            raise ValueError("MP4 데이터가 비어 있습니다.")

        try:
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

            with TemporaryDirectory(prefix="lecture_mp4_") as temp_dir:
                input_path = Path(temp_dir) / "input.mp4"
                input_path.write_bytes(mp4_bytes)

                # MP3를 파일로 만들지 않고 표준 출력(stdout)으로 전달한다.
                process = subprocess.run(
                    [
                        ffmpeg_path,
                        "-hide_banner",
                        "-loglevel", "error",
                        "-i", str(input_path),
                        "-vn",
                        "-codec:a", "libmp3lame",
                        "-q:a", "4",
                        "-f", "mp3",
                        "pipe:1",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )

                if process.returncode != 0:
                    error_message = process.stderr.decode(
                        "utf-8",
                        errors="replace",
                    )
                    raise RuntimeError(
                        f"FFmpeg 오디오 변환 실패: {error_message}"
                    )

                mp3_bytes = process.stdout

                if not mp3_bytes:
                    raise RuntimeError(
                        "MP4에서 추출한 MP3 데이터가 비어 있습니다."
                    )

                # 기존 MP3 전사 기능 재사용
                result = self.extract_text_from_mp3(
                    mp3_lecture_material=mp3_bytes,
                    language=language,
                )

                return result

        except Exception as exc:
            raise RuntimeError(
                f"MP4 음성 추출 또는 전사 실패: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

    def extract_text_from_url(self, url_lecture_material: str):
        pass


def get_lecture_material_text_extracter():
    return LectureMaterialTextExtracter()

def Test_extract_text_from_pdf():
    with open(
        "AmaddaBackend/웹인텔리전스와 탈중앙화.pdf",
        "rb",
    ) as file:
        pdf_bytes = file.read()

    extracter = get_lecture_material_text_extracter()
    result = extracter.extract_text_from_pdf(pdf_bytes)

    print(f"전체 페이지 수: {result['page_count']}")
    print("\n===== 전체 추출 텍스트 =====")
    print(result["full_text"])

def Test_extract_text_from_mp3():
    with open(
        "AmaddaBackend/종이_이전_기록_지식해적단.mp3",
        "rb",
    ) as file:
        mp3_bytes = file.read()

    extracter = get_lecture_material_text_extracter()
    result = extracter.extract_text_from_mp3(mp3_bytes)

    print(f"인식 언어: {result['language']}")
    print(f"음성 길이: {result['duration']}")
    print("\n===== 전체 추출 텍스트 =====")
    print(result["full_text"])

def Test_extract_text_from_mp4():
    with open(
        "AmaddaBackend/대가야_지식해적단.mp4",
        "rb",
    ) as file:
        mp4_bytes = file.read()

    extracter = get_lecture_material_text_extracter()
    result = extracter.extract_text_from_mp4(mp4_bytes)

    print(f"인식 언어: {result['language']}")

    if result["duration"] is not None:
        print(f"음성 길이: {result['duration']:.2f}초")

    print("\n===== 전체 추출 텍스트 =====")
    print(result["full_text"])

if __name__ == "__main__":
    from time import time

    time1 = time()
    Test_extract_text_from_mp4()
    time2 = time()

    print(f"\n처리 시간: {time2 - time1:.2f}초")

