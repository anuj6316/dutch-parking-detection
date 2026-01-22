import React, { useState, useRef } from 'react';
import { ChevronLeft, ChevronRight, Layers } from 'lucide-react';

interface TileComparisonSliderProps {
    images: string[];
    maskedImages: Map<number, string[]>;
}

/**
 * A component that displays one tile at a time with a draggable comparison slider
 * between the original and detection-overlay images.
 */
const TileComparisonSlider: React.FC<TileComparisonSliderProps> = ({ images, maskedImages }) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [sliderPosition, setSliderPosition] = useState(50); // Percentage
    const containerRef = useRef<HTMLDivElement>(null);

    const handlePrev = () => {
        setCurrentIndex(prev => (prev > 0 ? prev - 1 : images.length - 1));
    };

    const handleNext = () => {
        setCurrentIndex(prev => (prev < images.length - 1 ? prev + 1 : 0));
    };

    const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
        if (!containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const percentage = Math.min(Math.max((x / rect.width) * 100, 0), 100);
        setSliderPosition(percentage);
    };

    const handleTouchMove = (e: React.TouchEvent<HTMLDivElement>) => {
        if (!containerRef.current || !e.touches[0]) return;
        const rect = containerRef.current.getBoundingClientRect();
        const x = e.touches[0].clientX - rect.left;
        const percentage = Math.min(Math.max((x / rect.width) * 100, 0), 100);
        setSliderPosition(percentage);
    };

    const currentImage = images[currentIndex];
    const currentMask = maskedImages.get(currentIndex)?.[0];

    if (images.length === 0) return null;

    return (
        <div className="flex flex-col gap-4">
            {/* Tile Navigation */}
            <div className="flex items-center justify-between">
                <button
                    onClick={handlePrev}
                    className="p-2 rounded-full bg-card-lighter hover:bg-white/10 transition-colors text-white"
                >
                    <ChevronLeft size={20} />
                </button>
                <div className="flex items-center gap-2 text-white font-mono text-sm">
                    <Layers size={16} className="text-primary" />
                    Tile {currentIndex + 1} / {images.length}
                </div>
                <button
                    onClick={handleNext}
                    className="p-2 rounded-full bg-card-lighter hover:bg-white/10 transition-colors text-white"
                >
                    <ChevronRight size={20} />
                </button>
            </div>

            {/* Comparison Slider Container */}
            <div
                ref={containerRef}
                className="relative aspect-square w-full max-w-lg mx-auto rounded-xl overflow-hidden border border-white/10 cursor-ew-resize select-none"
                onMouseMove={handleMouseMove}
                onTouchMove={handleTouchMove}
            >
                {/* Layer 1: Detection Overlay (Clipped Right) */}
                <div className="absolute inset-0">
                    <img
                        src={currentImage}
                        alt="Original"
                        className="w-full h-full object-cover opacity-60"
                    />
                    {currentMask ? (
                        <img
                            src={currentMask}
                            alt="Detection Mask"
                            className="absolute inset-0 w-full h-full object-cover"
                        />
                    ) : (
                        <div className="absolute inset-0 flex items-center justify-center text-text-muted text-sm">
                            No Detections
                        </div>
                    )}
                </div>

                {/* Layer 2: Original Image (Clipped Left) */}
                <div
                    className="absolute inset-0 overflow-hidden"
                    style={{ clipPath: `inset(0 ${100 - sliderPosition}% 0 0)` }}
                >
                    <img
                        src={currentImage}
                        alt="Original Full"
                        className="w-full h-full object-cover"
                    />
                </div>

                {/* Slider Handle */}
                <div
                    className="absolute top-0 bottom-0 w-1 bg-white shadow-lg cursor-ew-resize z-10"
                    style={{ left: `${sliderPosition}%`, transform: 'translateX(-50%)' }}
                >
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white shadow-lg flex items-center justify-center">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                            <path d="M5 3L2 8L5 13" stroke="#333" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            <path d="M11 3L14 8L11 13" stroke="#333" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    </div>
                </div>

                {/* Labels */}
                <div className="absolute top-2 left-2 bg-black/70 backdrop-blur-sm px-2 py-1 rounded text-[10px] text-white font-mono">
                    Original
                </div>
                <div className="absolute top-2 right-2 bg-primary/80 backdrop-blur-sm px-2 py-1 rounded text-[10px] text-white font-mono">
                    Detections
                </div>
            </div>

            {/* Tile Dots Navigation */}
            <div className="flex justify-center gap-2">
                {images.map((_, idx) => (
                    <button
                        key={idx}
                        onClick={() => setCurrentIndex(idx)}
                        className={`w-2 h-2 rounded-full transition-all ${idx === currentIndex ? 'bg-primary scale-125' : 'bg-white/30 hover:bg-white/50'
                            }`}
                    />
                ))}
            </div>
        </div>
    );
};

export default TileComparisonSlider;