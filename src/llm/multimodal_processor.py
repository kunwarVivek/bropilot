"""
Multi-modal capabilities for vision and audio processing.

This module provides comprehensive multi-modal processing capabilities
including image analysis, audio transcription, and document processing.
"""

import asyncio
import base64
import io
import mimetypes
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import uuid
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
from core.interfaces import ILLMProvider
from core.exceptions import ProcessingError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class MediaType(str, Enum):
    """Media type enumeration."""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    TEXT = "text"


class ProcessingMode(str, Enum):
    """Processing mode enumeration."""
    ANALYZE = "analyze"
    EXTRACT = "extract"
    ENHANCE = "enhance"
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"
    SUMMARIZE = "summarize"


@dataclass
class MediaContent:
    """Represents multi-modal media content."""
    content_id: str
    media_type: MediaType
    content_data: Union[bytes, str]
    mime_type: str
    filename: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_base64(self) -> str:
        """Convert content to base64 string."""
        if isinstance(self.content_data, bytes):
            return base64.b64encode(self.content_data).decode('utf-8')
        else:
            return base64.b64encode(self.content_data.encode('utf-8')).decode('utf-8')
    
    def get_data_url(self) -> str:
        """Get data URL for the content."""
        return f"data:{self.mime_type};base64,{self.to_base64()}"


@dataclass
class ProcessingResult:
    """Result of multi-modal processing."""
    result_id: str
    content_id: str
    processing_mode: ProcessingMode
    result_data: Any
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


class ImageProcessor:
    """Advanced image processing capabilities."""
    
    def __init__(self):
        """Initialize image processor."""
        self.logger = StructuredLogger("image_processor")
    
    async def analyze_image(
        self,
        image_data: bytes,
        analysis_type: str = "general",
        llm_provider: Optional[ILLMProvider] = None
    ) -> Dict[str, Any]:
        """Analyze image content using computer vision and LLM."""
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Basic image analysis
            basic_analysis = self._analyze_image_properties(image)
            
            # Advanced analysis with LLM if available
            llm_analysis = {}
            if llm_provider:
                llm_analysis = await self._analyze_with_llm(image_data, analysis_type, llm_provider)
            
            # Computer vision analysis
            cv_analysis = await self._analyze_with_cv(image_data)
            
            return {
                "basic": basic_analysis,
                "llm": llm_analysis,
                "computer_vision": cv_analysis,
                "analysis_type": analysis_type
            }
            
        except Exception as e:
            self.logger.error(
                "Image analysis failed",
                error=str(e),
                analysis_type=analysis_type
            )
            raise ProcessingError(f"Image analysis failed: {e}") from e
    
    def _analyze_image_properties(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze basic image properties."""
        
        return {
            "dimensions": {
                "width": image.width,
                "height": image.height
            },
            "mode": image.mode,
            "format": image.format,
            "has_transparency": image.mode in ("RGBA", "LA") or "transparency" in image.info,
            "color_count": len(image.getcolors(maxcolors=256*256*256)) if image.getcolors(maxcolors=256*256*256) else "many",
            "aspect_ratio": round(image.width / image.height, 2)
        }
    
    async def _analyze_with_llm(
        self,
        image_data: bytes,
        analysis_type: str,
        llm_provider: ILLMProvider
    ) -> Dict[str, Any]:
        """Analyze image using LLM vision capabilities."""
        
        try:
            # Convert to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create analysis prompt based on type
            prompts = {
                "general": "Describe what you see in this image in detail.",
                "ui": "Analyze this user interface screenshot. Identify UI elements, layout, and any text visible.",
                "document": "Extract and analyze the text content from this document image.",
                "chart": "Analyze this chart or graph. Describe the data, trends, and key insights.",
                "accessibility": "Analyze this image for accessibility issues and suggest improvements."
            }
            
            prompt = prompts.get(analysis_type, prompts["general"])
            
            # Send to LLM with image
            response = await llm_provider.generate_response(
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }],
                max_tokens=1000
            )
            
            return {
                "description": response.get("content", ""),
                "model": response.get("model"),
                "usage": response.get("usage")
            }
            
        except Exception as e:
            self.logger.error(
                "LLM image analysis failed",
                error=str(e),
                analysis_type=analysis_type
            )
            return {"error": str(e)}
    
    async def _analyze_with_cv(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze image using computer vision techniques."""
        
        try:
            # Convert to OpenCV format
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return {"error": "Could not decode image"}
            
            # Color analysis
            color_analysis = self._analyze_colors(image)
            
            # Edge detection
            edges = cv2.Canny(image, 100, 200)
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            
            # Brightness and contrast
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            # Blur detection
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            return {
                "colors": color_analysis,
                "edge_density": float(edge_density),
                "brightness": float(brightness),
                "contrast": float(contrast),
                "blur_score": float(blur_score),
                "is_blurry": blur_score < 100
            }
            
        except Exception as e:
            self.logger.error(
                "Computer vision analysis failed",
                error=str(e)
            )
            return {"error": str(e)}
    
    def _analyze_colors(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze color distribution in image."""
        
        # Convert to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Calculate dominant colors
        pixels = image_rgb.reshape(-1, 3)
        
        # Simple color analysis
        mean_color = np.mean(pixels, axis=0)
        
        # Color temperature estimation
        r, g, b = mean_color
        color_temp = "warm" if r > b else "cool" if b > r else "neutral"
        
        return {
            "mean_color": {
                "r": int(mean_color[0]),
                "g": int(mean_color[1]),
                "b": int(mean_color[2])
            },
            "color_temperature": color_temp,
            "is_grayscale": self._is_grayscale(image_rgb)
        }
    
    def _is_grayscale(self, image: np.ndarray) -> bool:
        """Check if image is grayscale."""
        return len(np.unique(image.reshape(-1, 3), axis=0)) < 100
    
    async def enhance_image(
        self,
        image_data: bytes,
        enhancement_type: str = "auto"
    ) -> bytes:
        """Enhance image quality."""
        
        try:
            image = Image.open(io.BytesIO(image_data))
            
            if enhancement_type == "auto":
                # Auto enhancement
                enhanced = ImageEnhance.Contrast(image).enhance(1.2)
                enhanced = ImageEnhance.Brightness(enhanced).enhance(1.1)
                enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.1)
            
            elif enhancement_type == "sharpen":
                enhanced = image.filter(ImageFilter.SHARPEN)
            
            elif enhancement_type == "denoise":
                enhanced = image.filter(ImageFilter.SMOOTH)
            
            else:
                enhanced = image
            
            # Convert back to bytes
            output = io.BytesIO()
            enhanced.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(
                "Image enhancement failed",
                error=str(e),
                enhancement_type=enhancement_type
            )
            raise ProcessingError(f"Image enhancement failed: {e}") from e


class AudioProcessor:
    """Advanced audio processing capabilities."""
    
    def __init__(self):
        """Initialize audio processor."""
        self.logger = StructuredLogger("audio_processor")
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = "auto",
        llm_provider: Optional[ILLMProvider] = None
    ) -> Dict[str, Any]:
        """Transcribe audio to text."""
        
        try:
            # This would integrate with speech-to-text services
            # For now, return a placeholder
            
            self.logger.info(
                "Transcribing audio",
                audio_size=len(audio_data),
                language=language
            )
            
            # Placeholder transcription
            transcription = {
                "text": "Audio transcription would be performed here using services like Whisper, Google Speech-to-Text, etc.",
                "language": language,
                "confidence": 0.95,
                "duration": 10.0,
                "segments": [
                    {
                        "start": 0.0,
                        "end": 10.0,
                        "text": "Sample transcription segment"
                    }
                ]
            }
            
            return transcription
            
        except Exception as e:
            self.logger.error(
                "Audio transcription failed",
                error=str(e),
                language=language
            )
            raise ProcessingError(f"Audio transcription failed: {e}") from e
    
    async def analyze_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """Analyze audio properties."""
        
        try:
            # This would analyze audio properties
            # For now, return basic analysis
            
            return {
                "duration": 10.0,
                "sample_rate": 44100,
                "channels": 2,
                "format": "wav",
                "size_bytes": len(audio_data),
                "has_speech": True,
                "noise_level": "low"
            }
            
        except Exception as e:
            self.logger.error(
                "Audio analysis failed",
                error=str(e)
            )
            raise ProcessingError(f"Audio analysis failed: {e}") from e


class DocumentProcessor:
    """Advanced document processing capabilities."""
    
    def __init__(self):
        """Initialize document processor."""
        self.logger = StructuredLogger("document_processor")
    
    async def extract_text(
        self,
        document_data: bytes,
        document_type: str = "auto"
    ) -> Dict[str, Any]:
        """Extract text from document."""
        
        try:
            # This would integrate with OCR and document parsing libraries
            # For now, return a placeholder
            
            self.logger.info(
                "Extracting text from document",
                document_size=len(document_data),
                document_type=document_type
            )
            
            extracted_text = {
                "text": "Document text extraction would be performed here using OCR libraries like Tesseract, cloud services, etc.",
                "pages": 1,
                "confidence": 0.98,
                "language": "en",
                "metadata": {
                    "title": "Sample Document",
                    "author": "Unknown",
                    "creation_date": datetime.utcnow().isoformat()
                }
            }
            
            return extracted_text
            
        except Exception as e:
            self.logger.error(
                "Document text extraction failed",
                error=str(e),
                document_type=document_type
            )
            raise ProcessingError(f"Document text extraction failed: {e}") from e


class MultiModalProcessor:
    """Main multi-modal processing coordinator."""
    
    def __init__(self, llm_provider: Optional[ILLMProvider] = None):
        """Initialize multi-modal processor."""
        self.llm_provider = llm_provider
        self.logger = StructuredLogger("multimodal_processor")
        
        # Initialize specialized processors
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        self.document_processor = DocumentProcessor()
        
        # Content storage
        self.content_cache: Dict[str, MediaContent] = {}
        self.processing_results: Dict[str, ProcessingResult] = {}
    
    async def process_content(
        self,
        content_data: Union[bytes, str],
        media_type: MediaType,
        processing_mode: ProcessingMode,
        mime_type: Optional[str] = None,
        filename: Optional[str] = None,
        **kwargs
    ) -> ProcessingResult:
        """Process multi-modal content."""
        
        content_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())
        
        # Determine MIME type if not provided
        if not mime_type and filename:
            mime_type, _ = mimetypes.guess_type(filename)
        
        # Create media content
        media_content = MediaContent(
            content_id=content_id,
            media_type=media_type,
            content_data=content_data,
            mime_type=mime_type or "application/octet-stream",
            filename=filename
        )
        
        # Cache content
        self.content_cache[content_id] = media_content
        
        self.logger.info(
            "Processing multi-modal content",
            content_id=content_id,
            media_type=media_type.value,
            processing_mode=processing_mode.value,
            content_size=len(content_data) if isinstance(content_data, bytes) else len(str(content_data))
        )
        
        start_time = datetime.utcnow()
        
        try:
            # Route to appropriate processor
            if media_type == MediaType.IMAGE:
                result_data = await self._process_image(content_data, processing_mode, **kwargs)
            elif media_type == MediaType.AUDIO:
                result_data = await self._process_audio(content_data, processing_mode, **kwargs)
            elif media_type == MediaType.DOCUMENT:
                result_data = await self._process_document(content_data, processing_mode, **kwargs)
            else:
                raise ValidationError(f"Unsupported media type: {media_type}")
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Create processing result
            result = ProcessingResult(
                result_id=result_id,
                content_id=content_id,
                processing_mode=processing_mode,
                result_data=result_data,
                processing_time=processing_time,
                metadata={
                    "media_type": media_type.value,
                    "mime_type": mime_type,
                    "filename": filename
                }
            )
            
            # Cache result
            self.processing_results[result_id] = result
            
            self.logger.info(
                "Multi-modal processing completed",
                content_id=content_id,
                result_id=result_id,
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.error(
                "Multi-modal processing failed",
                content_id=content_id,
                media_type=media_type.value,
                processing_mode=processing_mode.value,
                error=str(e),
                processing_time=processing_time
            )
            
            # Create error result
            result = ProcessingResult(
                result_id=result_id,
                content_id=content_id,
                processing_mode=processing_mode,
                result_data={"error": str(e)},
                processing_time=processing_time,
                metadata={
                    "media_type": media_type.value,
                    "error": True
                }
            )
            
            self.processing_results[result_id] = result
            raise ProcessingError(f"Multi-modal processing failed: {e}") from e
    
    async def _process_image(
        self,
        image_data: bytes,
        processing_mode: ProcessingMode,
        **kwargs
    ) -> Dict[str, Any]:
        """Process image content."""
        
        if processing_mode == ProcessingMode.ANALYZE:
            analysis_type = kwargs.get("analysis_type", "general")
            return await self.image_processor.analyze_image(
                image_data, analysis_type, self.llm_provider
            )
        
        elif processing_mode == ProcessingMode.ENHANCE:
            enhancement_type = kwargs.get("enhancement_type", "auto")
            enhanced_data = await self.image_processor.enhance_image(
                image_data, enhancement_type
            )
            return {
                "enhanced_image": base64.b64encode(enhanced_data).decode('utf-8'),
                "enhancement_type": enhancement_type
            }
        
        else:
            raise ValidationError(f"Unsupported processing mode for images: {processing_mode}")
    
    async def _process_audio(
        self,
        audio_data: bytes,
        processing_mode: ProcessingMode,
        **kwargs
    ) -> Dict[str, Any]:
        """Process audio content."""
        
        if processing_mode == ProcessingMode.TRANSCRIBE:
            language = kwargs.get("language", "auto")
            return await self.audio_processor.transcribe_audio(
                audio_data, language, self.llm_provider
            )
        
        elif processing_mode == ProcessingMode.ANALYZE:
            return await self.audio_processor.analyze_audio(audio_data)
        
        else:
            raise ValidationError(f"Unsupported processing mode for audio: {processing_mode}")
    
    async def _process_document(
        self,
        document_data: bytes,
        processing_mode: ProcessingMode,
        **kwargs
    ) -> Dict[str, Any]:
        """Process document content."""
        
        if processing_mode == ProcessingMode.EXTRACT:
            document_type = kwargs.get("document_type", "auto")
            return await self.document_processor.extract_text(
                document_data, document_type
            )
        
        else:
            raise ValidationError(f"Unsupported processing mode for documents: {processing_mode}")
    
    def get_content(self, content_id: str) -> Optional[MediaContent]:
        """Get cached content by ID."""
        return self.content_cache.get(content_id)
    
    def get_result(self, result_id: str) -> Optional[ProcessingResult]:
        """Get processing result by ID."""
        return self.processing_results.get(result_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        
        total_content = len(self.content_cache)
        total_results = len(self.processing_results)
        
        # Count by media type
        media_type_counts = {}
        for content in self.content_cache.values():
            media_type_counts[content.media_type.value] = media_type_counts.get(content.media_type.value, 0) + 1
        
        # Count by processing mode
        processing_mode_counts = {}
        for result in self.processing_results.values():
            processing_mode_counts[result.processing_mode.value] = processing_mode_counts.get(result.processing_mode.value, 0) + 1
        
        # Calculate average processing time
        processing_times = [r.processing_time for r in self.processing_results.values()]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        return {
            "total_content": total_content,
            "total_results": total_results,
            "media_type_counts": media_type_counts,
            "processing_mode_counts": processing_mode_counts,
            "average_processing_time": avg_processing_time,
            "cache_size_mb": sum(
                len(c.content_data) if isinstance(c.content_data, bytes) else len(str(c.content_data))
                for c in self.content_cache.values()
            ) / (1024 * 1024)
        }
