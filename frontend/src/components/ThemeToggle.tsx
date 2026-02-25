import { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

const ThemeToggle = () => {
    const [isDark, setIsDark] = useState(() => {
        if (typeof window !== 'undefined') {
            return document.documentElement.classList.contains('dark') || localStorage.getItem('theme') === 'dark';
        }
        return false;
    });

    useEffect(() => {
        const root = window.document.documentElement;
        if (isDark) {
            root.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            root.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    }, [isDark]);

    return (
        <button
            onClick={() => setIsDark(!isDark)}
            className="relative p-2 rounded-xl hover:bg-gray-200/80 dark:hover:bg-gray-700/50 transition-all duration-200 group"
            aria-label="Toggle Theme"
        >
            <div className="relative w-5 h-5">
                <Sun
                    className={`w-5 h-5 text-amber-500 absolute inset-0 transition-all duration-300 ${isDark ? 'opacity-100 rotate-0 scale-100' : 'opacity-0 -rotate-90 scale-50'
                        }`}
                />
                <Moon
                    className={`w-5 h-5 text-gray-500 dark:text-gray-400 absolute inset-0 transition-all duration-300 ${isDark ? 'opacity-0 rotate-90 scale-50' : 'opacity-100 rotate-0 scale-100'
                        }`}
                />
            </div>
        </button>
    );
};

export default ThemeToggle;
