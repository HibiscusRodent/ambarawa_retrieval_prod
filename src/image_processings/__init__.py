"""
Image Processing Module

This module provides tools for processing images and PDFs, including:
- Loading and processing images from book folders
- Converting images to various formats (base64, binary, BAML)
- Resizing and optimizing images
- Handling both individual images and PDF documents

Main Classes:
    ImageProcessors: The primary class for all image processing operations
    ProcessedBookDict: TypedDict for structured book processing results
"""

from image_processings.main import ImageProcessors

__all__: list[str] = ["ImageProcessors"]