import csv
from src.utils import clean_word


def preprocess_words(input_path: str, output_path: str):
    words = set()

    # đọc file txt
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            word = clean_word(line)

            if word:  # bỏ dòng rỗng
                words.add(word)

    words = sorted(words)
    print("Unique words:", len(words))

    # ghi csv
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "word",
            "count_correct",
            "count_appear",
            "count_incorrect"
        ])

        for w in words:
            writer.writerow([w, 0, 0, 0])
