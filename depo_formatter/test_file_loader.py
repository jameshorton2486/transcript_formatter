import tempfile
import unittest
from pathlib import Path

from docx import Document

from file_loader import (
    assemble_block,
    build_speaker_map,
    detect_speaker_label,
    parse_deepgram_docx,
)


class FileLoaderTests(unittest.TestCase):
    def test_detect_speaker_label(self) -> None:
        self.assertEqual(detect_speaker_label("Speaker 0:"), 0)
        self.assertEqual(detect_speaker_label("Speaker 1:"), 1)
        self.assertEqual(detect_speaker_label("Speaker 2"), 2)
        self.assertIsNone(detect_speaker_label("I went to the site."))
        self.assertIsNone(detect_speaker_label(""))

    def test_assemble_block_splits_sentences(self) -> None:
        speaker_id, paragraphs = assemble_block(
            1,
            [
                "I went to the site on April 7th.",
                "The conditions were unsafe.",
                "Nobody told me to stop work.",
            ],
        )
        self.assertEqual(speaker_id, 1)
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual(paragraphs[0], "I went to the site on April 7th.")

    def test_assemble_block_keeps_abbreviation_sentence_together(self) -> None:
        _, paragraphs = assemble_block(
            2,
            ["Dr. Smith confirmed the diagnosis. The report was filed."],
        )
        self.assertEqual(len(paragraphs), 2)
        self.assertEqual(paragraphs[0], "Dr. Smith confirmed the diagnosis.")

    def test_build_speaker_map_uses_keywords(self) -> None:
        test_blocks = [
            (1, ["I am John Smith, I represent the plaintiff."]),
            (2, ["Raise your right hand please."]),
            (0, ["We are now on the record."]),
            (3, ["My name is Jane Doe, counsel for the defendant."]),
            (4, ["I arrived at the property around eight.", "Nobody warned me about the hazard."]),
            (4, ["I spoke with the supervisor after the fall."]),
        ]

        speaker_map = build_speaker_map(test_blocks)
        self.assertEqual(speaker_map.lead_attorney, 1)
        self.assertEqual(speaker_map.court_reporter, 2)
        self.assertEqual(speaker_map.videographer, 0)
        self.assertEqual(speaker_map.opposing_attorney, 3)
        self.assertEqual(speaker_map.witness, 4)

    def test_parse_deepgram_docx_builds_blocks_and_map(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "deepgram.docx"
            document = Document()
            for paragraph in [
                "Speaker 1:",
                "I am John Smith, I represent the plaintiff.",
                "Speaker 2:",
                "Raise your right hand please.",
                "Speaker 4:",
                "I went to the site on April 7th.",
                "The conditions were unsafe.",
                "Speaker 0:",
                "We are now on the record.",
            ]:
                document.add_paragraph(paragraph)
            document.save(docx_path)

            blocks, speaker_map = parse_deepgram_docx(str(docx_path))

        self.assertEqual(len(blocks), 4)
        self.assertEqual(blocks[0][0], 1)
        self.assertEqual(
            blocks[2],
            (4, ["I went to the site on April 7th.", "The conditions were unsafe."]),
        )
        self.assertEqual(speaker_map.lead_attorney, 1)
        self.assertEqual(speaker_map.court_reporter, 2)
        self.assertEqual(speaker_map.videographer, 0)
        self.assertEqual(speaker_map.witness, 4)


if __name__ == "__main__":
    unittest.main()
