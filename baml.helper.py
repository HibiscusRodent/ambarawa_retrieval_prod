from image_processors import ImageProcessors

# from baml_py import Image, Collector  # Unused in this helper script
from dotenv import load_dotenv

env_loader = load_dotenv()
book_folder_path = r"sample_data\rak-0003_baris-005_buku-30"


processor = ImageProcessors()
base64_images, binary_images = processor.process_book_folder(
    book_folder=book_folder_path
)
print("-" * 20)
print(f"FINAL RESULT - Base64 images count: {len(base64_images)}")
print(f"FINAL RESULT - Binary images count: {len(binary_images)}")
print("-" * 20)
