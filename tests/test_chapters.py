"""chapters.py: Russian titles and chapters spread over a long video (P5)."""
import os, tempfile, unittest

from helpers import fixture, run_json


def long_srt(path, topics, cues_per_topic, sec=4.0):
    """A long synthetic talk: each topic is many lines of its own vocabulary, no pauses at all."""
    lines, t, n = [], 0.0, 1
    for words in topics:
        for i in range(cues_per_topic):
            a, b = t, t + sec - 0.05
            ts = lambda x: f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round(x % 1 * 1000)):03d}"
            lines.append(f"{n}\n{ts(a)} --> {ts(b)}\n{words[i % len(words)]}\n")
            t += sec; n += 1
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


class Russian(unittest.TestCase):
    def test_titles_are_topic_words(self):
        r = run_json("yt-chapters/chapters.py", fixture("ru", "chapters_ru_flat.srt"), "--target", "4")
        titles = [c["draft_title"].lower() for c in r["chapters"]]
        for word, title in zip(("камер", "монтаж", "обложк", "рекомендац"), titles):
            self.assertIn(word, title)
        self.assertTrue(r["valid"])

    def test_long_video_is_not_chaptered_in_one_corner(self):
        topics = [["Сначала про свет и камеру", "Свет ставлю слева от камеры"],
                  ["Теперь про звук и микрофон", "Микрофон держу близко ко рту"],
                  ["Дальше монтаж и склейки", "Склейки делаю на таймлайне"],
                  ["Потом обложка и заголовок", "Обложку рисую в конце"],
                  ["И наконец продвижение и рекомендации", "Рекомендации приводят зрителей"]]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "long.srt")
            long_srt(path, topics, 150)          # 5 topics x 10 minutes, no pauses anywhere
            r = run_json("yt-chapters/chapters.py", path, "--target", "5")
        starts = [c["start"] for c in r["chapters"]]
        for want, got in zip([0, 600, 1200, 1800, 2400], starts):
            self.assertLessEqual(abs(want - got), 60, starts)


if __name__ == "__main__":
    unittest.main()
