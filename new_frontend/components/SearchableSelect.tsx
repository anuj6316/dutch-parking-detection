import React, { useState, useRef, useEffect } from 'react';
import { Check, ChevronsUpDown, Search } from 'lucide-react';

interface Option {
    id: string;
    label: string;
}

interface SearchableSelectProps {
    options: Option[];
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    className?: string;
}

const SearchableSelect: React.FC<SearchableSelectProps> = ({
    options,
    value,
    onChange,
    placeholder = "Select option...",
    className = ""
}) => {
    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState("");
    const wrapperRef = useRef<HTMLDivElement>(null);

    const filteredOptions = options.filter(option =>
        option.label.toLowerCase().includes(search.toLowerCase())
    );

    const selectedOption = options.find(option => option.id === value);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
                setOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <div className={`relative ${className}`} ref={wrapperRef}>
            <button
                type="button"
                onClick={() => setOpen(!open)}
                className="flex items-center justify-between w-full px-3 py-2 bg-[#1c2128] border border-card-border rounded-lg text-sm text-white hover:border-primary/50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
                <span className="truncate mr-2 font-bold">
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <ChevronsUpDown size={14} className="text-text-muted shrink-0" />
            </button>

            {open && (
                <div className="absolute z-[3000] w-full mt-1 bg-[#1c2128] border border-card-border rounded-lg shadow-xl max-h-[300px] flex flex-col animate-in fade-in zoom-in-95 duration-100">
                    <div className="p-2 border-b border-white/5 sticky top-0 bg-[#1c2128]">
                        <div className="flex items-center gap-2 px-2 py-1.5 bg-black/20 rounded-md border border-white/5">
                            <Search size={14} className="text-text-muted" />
                            <input
                                type="text"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Search..."
                                className="w-full bg-transparent border-none text-xs text-white placeholder:text-white/20 focus:outline-none focus:ring-0"
                                autoFocus
                            />
                        </div>
                    </div>
                    
                    <div className="overflow-y-auto flex-1 p-1">
                        {filteredOptions.length === 0 ? (
                            <div className="px-2 py-3 text-xs text-center text-text-muted italic">
                                No results found.
                            </div>
                        ) : (
                            filteredOptions.map((option) => (
                                <button
                                    key={option.id}
                                    onClick={() => {
                                        onChange(option.id);
                                        setOpen(false);
                                        setSearch("");
                                    }}
                                    className={`w-full text-left px-2 py-1.5 rounded-md text-xs font-medium flex items-center justify-between transition-colors ${
                                        value === option.id
                                            ? "bg-primary text-white"
                                            : "text-text-muted hover:bg-white/5 hover:text-white"
                                    }`}
                                >
                                    {option.label}
                                    {value === option.id && <Check size={14} />}
                                </button>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default SearchableSelect;
