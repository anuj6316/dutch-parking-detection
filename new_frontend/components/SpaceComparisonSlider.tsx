import React, { useState, useRef } from 'react';
import { ChevronLeft, ChevronRight, Car, Eye, EyeOff } from 'lucide-react';
import { Space } from '../types';

interface SpaceComparisonSliderProps {
    spaces: Space[];
}

/**
 * A component that displays one parking space at a time with a draggable comparison slider
 * between the original cropped image and the detection overlay.
 */
const SpaceComparisonSlider: React.FC<SpaceComparisonSliderProps> = ({ spaces }) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [sliderPosition, setSliderPosition] = useState(50);
    const containerRef = useRef<HTMLDivElement>(null);

    // Filter to only spaces that have cropped images
    const spacesWithImages = spaces.filter(s => s.croppedImage);

    const handlePrev = () => {
        setCurrentIndex(prev => (prev > 0 ? prev - 1 : spacesWithImages.length - 1));
    };

    const handleNext = () => {
        setCurrentIndex(prev => (prev < spacesWithImages.length - 1 ? prev + 1 : 0));
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

    if (spacesWithImages.length === 0) {
        return (
            <div className="flex items-center justify-center p-8 text-text-muted text-sm">
                <Car size={16} className="mr-2" />
                No cropped images available. Run analysis to see results.
            </div>
        );
    }

    const currentSpace = spacesWithImages[currentIndex];
    const normalizedConfidence = Math.round(80 + (currentSpace.confidence / 100) * 20);

    return (
        <div className="flex flex-col gap-4">
            {/* Space Navigation */}
            <div className="flex items-center justify-between">
                <button
                    onClick={handlePrev}
                    className="p-2 rounded-full bg-card-lighter hover:bg-white/10 transition-colors text-white"
                >
                    <ChevronLeft size={20} />
                </button>
                <div className="flex items-center gap-2 text-white font-mono text-sm">
                    <Car size={16} className="text-[#0bda95]" />
                    <span className="text-[#0bda95]">
                        {currentSpace.id}
                    </span>
                    <span className="text-text-muted">
                        ({currentIndex + 1} / {spacesWithImages.length})
                    </span>
                </div>
                <button
                    onClick={handleNext}
                    className="p-2 rounded-full bg-card-lighter hover:bg-white/10 transition-colors text-white"
                >
                    <ChevronRight size={20} />
                </button>
            </div>

            {/* Status Badge */}
            <div className="flex justify-center gap-3">
                <span className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset bg-[#0bda95]/10 text-[#0bda95] ring-[#0bda95]/20">
                    {currentSpace.status}
                </span>
                <span className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium bg-white/5 text-white ring-1 ring-white/10">
                    🚗 {currentSpace.vehicleCount ?? 0} Vehicle{(currentSpace.vehicleCount ?? 0) !== 1 ? 's' : ''}
                </span>
                <span className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium bg-blue-500/10 text-blue-400 ring-1 ring-blue-500/20">
                    {normalizedConfidence}% Confidence
                </span>
            </div>

            {/* Comparison Slider Container */}
            <div
                ref={containerRef}
                className="relative aspect-video w-full max-w-lg mx-auto rounded-xl overflow-hidden border border-white/10 cursor-ew-resize select-none bg-black"
                onMouseMove={handleMouseMove}
                onTouchMove={handleTouchMove}
            >
                {/* Layer 1: Detection Overlay (Right side) */}
                <div className="absolute inset-0">
                    {currentSpace.croppedOverlay ? (
                        <img
                            src={currentSpace.croppedOverlay}
                            alt="Detection Overlay"
                            className="w-full h-full object-contain"
                        />
                    ) : currentSpace.croppedImage ? (
                        <img
                            src={currentSpace.croppedImage}
                            alt="Original"
                            className="w-full h-full object-contain opacity-60"
                        />
                    ) : (
                        <div className="flex items-center justify-center h-full text-text-muted">
                            No Image
                        </div>
                    )}
                </div>

                {/* Layer 2: Original Image (Left side, clipped) */}
                {currentSpace.croppedImage && (
                    <div
                        className="absolute inset-0 overflow-hidden"
                        style={{ clipPath: `inset(0 ${100 - sliderPosition}% 0 0)` }}
                    >
                        <img
                            src={currentSpace.croppedImage}
                            alt="Original"
                            className="w-full h-full object-contain"
                        />
                    </div>
                )}

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
                <div className="absolute top-2 left-2 bg-black/70 backdrop-blur-sm px-2 py-1 rounded text-[10px] text-white font-mono flex items-center gap-1">
                    <EyeOff size={10} /> Original
                </div>
                <div className="absolute top-2 right-2 bg-[#22c55e]/80 backdrop-blur-sm px-2 py-1 rounded text-[10px] text-white font-mono flex items-center gap-1">
                    <Eye size={10} /> Detections
                </div>
            </div>

            {/* Dots Navigation */}
            <div className="flex justify-center gap-2 flex-wrap max-w-lg mx-auto">
                {spacesWithImages.slice(0, 20).map((space, idx) => (
                    <button
                        key={space.id}
                        onClick={() => setCurrentIndex(idx)}
                        className={`w-2 h-2 rounded-full transition-all ${idx === currentIndex
                                ? 'bg-[#0bda95] scale-125'
                                : 'bg-white/30 hover:bg-white/50'
                            }`}
                        title={`${space.id} - ${space.status}`}
                    />
                ))}
                {spacesWithImages.length > 20 && (
                    <span className="text-text-muted text-xs">+{spacesWithImages.length - 20} more</span>
                )}
            </div>
        </div>
    );
};

export default SpaceComparisonSlider;