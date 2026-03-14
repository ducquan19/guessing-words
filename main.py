from src.preprocess import preprocess_words

INPUT_FILE = "data/raw/words.txt"
OUTPUT_FILE = "data/processed/words.csv"


if __name__ == "__main__":
    preprocess_words(INPUT_FILE, OUTPUT_FILE)
    print("Preprocessing completed.")
