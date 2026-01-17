import { CheckCircle, Film, ChevronRight } from 'lucide-react';

export default function ResultsSection({ results }) {
    console.log("ResultsSection received:", results);

    if (!results) {
        return (
            <div className="text-center p-12 text-slate-400">
                <p>Waiting for results data...</p>
                <span className="text-xs opacity-50">(If this persists, check console logs)</span>
            </div>
        );
    }

    // Helper to format seconds into MM:SS
    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="animate-slide-up space-y-8 pb-12 max-w-7xl mx-auto px-6 md:px-12" style={{ animationDelay: '0.1s' }}>
            <div className="flex items-center gap-4 border-b border-slate-800 pb-4">
                <CheckCircle className="w-6 h-6 text-green-400" />
                <h3 className="text-2xl font-bold text-white">AI Edit Plan Generated</h3>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Transcript Side */}
                <div className="space-y-4">
                    <h4 className="text-lg font-medium text-slate-400 uppercase tracking-wider text-sm mb-4">Original Narrative Flow</h4>
                    <div className="space-y-4">
                        {/* Map 'transcript' */}
                        {results.transcript?.map((item, idx) => (
                            <div key={idx} className="glass-card p-6 rounded-xl flex gap-4 hover:bg-slate-800/60 transition-colors">
                                <span className="text-blue-400 font-mono text-sm whitespace-nowrap">
                                    {formatTime(item.start)}
                                </span>
                                <p className="text-slate-300 leading-relaxed">{item.text}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* B-Roll Plan Side */}
                <div className="space-y-4">
                    <h4 className="text-lg font-medium text-slate-400 uppercase tracking-wider text-sm mb-4">Suggested Visual Overlays</h4>
                    <div className="space-y-4">
                        {/* Map 'timeline' */}
                        {results.timeline?.map((edit, idx) => (
                            <div key={idx} className="glass-card p-6 rounded-xl border-l-4 border-l-purple-500 hover:bg-slate-800/60 transition-colors group">
                                <div className="flex justify-between items-start mb-3">
                                    <div className="flex items-center gap-2">
                                        <Film className="w-4 h-4 text-purple-400" />
                                        {/* Use 'b_roll_id' */}
                                        <span className="font-semibold text-slate-200">{edit.b_roll_id}</span>
                                    </div>
                                    <span className="px-2 py-1 rounded bg-green-500/20 text-green-400 text-xs font-bold">
                                        {(edit.confidence * 100).toFixed(0)}% Match
                                    </span>
                                </div>
                                <p className="text-slate-400 text-sm mb-3">{edit.reason}</p>
                                <div className="flex items-center justify-between mt-4 text-xs text-slate-500 border-t border-slate-800 pt-3">
                                    {/* Use 'a_roll_start' */}
                                    <span className="font-mono">Overlay at: {formatTime(edit.a_roll_start)}</span>
                                    {/* <button className="flex items-center gap-1 text-purple-400 hover:text-purple-300 transition-colors">
                                        Preview <ChevronRight className="w-3 h-3" />
                                    </button> */}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
