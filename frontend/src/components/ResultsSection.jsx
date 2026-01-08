import { CheckCircle, Film, ChevronRight } from 'lucide-react';

export default function ResultsSection({ results }) {
    if (!results) return null;

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
                        {results.transcripts?.map((item, idx) => (
                            <div key={idx} className="glass-card p-6 rounded-xl flex gap-4 hover:bg-slate-800/60 transition-colors">
                                <span className="text-blue-400 font-mono text-sm whitespace-nowrap">{item.time}</span>
                                <p className="text-slate-300 leading-relaxed">{item.text}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* B-Roll Plan Side */}
                <div className="space-y-4">
                    <h4 className="text-lg font-medium text-slate-400 uppercase tracking-wider text-sm mb-4">Suggested Visual Overlays</h4>
                    <div className="space-y-4">
                        {results.edits?.map((edit, idx) => (
                            <div key={idx} className="glass-card p-6 rounded-xl border-l-4 border-l-purple-500 hover:bg-slate-800/60 transition-colors group">
                                <div className="flex justify-between items-start mb-3">
                                    <div className="flex items-center gap-2">
                                        <Film className="w-4 h-4 text-purple-400" />
                                        <span className="font-semibold text-slate-200">{edit.b_roll}</span>
                                    </div>
                                    <span className="px-2 py-1 rounded bg-green-500/20 text-green-400 text-xs font-bold">
                                        {edit.confidence}% Match
                                    </span>
                                </div>
                                <p className="text-slate-400 text-sm mb-3">{edit.reason}</p>
                                <div className="flex items-center justify-between mt-4 text-xs text-slate-500 border-t border-slate-800 pt-3">
                                    <span className="font-mono">Overlay at: {edit.time}</span>
                                    <button className="flex items-center gap-1 text-purple-400 hover:text-purple-300 transition-colors">
                                        Preview <ChevronRight className="w-3 h-3" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
