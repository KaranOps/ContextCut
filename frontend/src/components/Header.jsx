import { Sparkles } from 'lucide-react';

export default function Header() {
    return (
        <header className="text-center space-y-4 animate-fade-in">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-900 border border-purple-500/20 shadow-lg shadow-purple-900/10">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span className="text-xs font-medium text-purple-200 uppercase tracking-wider">AI Director Mode</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight">
                Context<span className="text-gradient">Cut</span>
            </h1>
            <p className="text-slate-400 text-lg md:text-xl font-light tracking-wide">
                Intelligent Video Sync & Narrative Orchestration
            </p>
        </header>
    );
}
