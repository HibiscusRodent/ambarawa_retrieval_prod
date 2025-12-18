from pathlib import Path
from image_processors import ImageProcessors, BookFolderPathData

# from baml_py import Image, Collector  # Unused in this helper script
from dotenv import load_dotenv
import logfire

logfire.configure()

env_loader = load_dotenv()
book_folder_path = r"sample_data\rak-0003_baris-005_buku-30"


processor = ImageProcessors()
folder_data = BookFolderPathData(path=Path(book_folder_path))
processed_data = processor.process_book_folder(folder_data=folder_data)

print("-" * 20)
print(f"FINAL RESULT - Book ID: {processed_data.book_id}")
print(f"FINAL RESULT - Base64 images count: {len(processed_data.base64_images)}")
print(f"FINAL RESULT - Binary images count: {len(processed_data.binary_images)}")
print("-" * 20)
