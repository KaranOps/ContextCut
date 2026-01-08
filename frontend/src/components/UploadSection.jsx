import { Upload, Film, FileVideo, Sparkles, X, Play } from 'lucide-react';

export default function UploadSection({
    aRollFile,
    bRollFiles,
    handleARollChange,
    handleBRollChange,
    removeBRoll,
    onGenerate,
    isGenerating
}) {
    return (
        <div className="max-w-7xl mx-auto px-6 md:px-12 space-y-12">
            {/* Upload Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 animate-slide-up" style={{ animationDelay: '0.1s' }}>

                {/* A-Roll Container */}
                <div className="group relative">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl opacity-20 group-hover:opacity-40 transition duration-500 blur"></div>
                    <div className="relative glass-card rounded-2xl p-8 h-full min-h-[400px] flex flex-col">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="p-3 bg-blue-500/10 rounded-xl">
                                <FileVideo className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold text-slate-100">1. Main A-Roll</h2>
                                <p className="text-slate-500 text-sm">Primary narrative footage</p>
                            </div>
                        </div>

                        {aRollFile ? (
                            <div className="flex-1 flex flex-col items-center justify-center p-8 border border-slate-700 bg-slate-800/50 rounded-xl space-y-4">
                                <div className="w-16 h-16 rounded-full bg-blue-500/20 flex items-center justify-center">
                                    <Play className="w-8 h-8 text-blue-400 ml-1" />
                                </div>
                                <div className="text-center">
                                    <p className="font-medium text-lg text-slate-200 break-all">{aRollFile.name}</p>
                                    <p className="text-slate-500">{(aRollFile.size / (1024 * 1024)).toFixed(1)} MB</p>
                                </div>
                                <button
                                    onClick={() => handleARollChange({ target: { files: [] } })}
                                    className="mt-4 px-4 py-2 hover:bg-red-500/10 text-red-400 rounded-lg text-sm transition-colors"
                                >
                                    Remove File
                                </button>
                            </div>
                        ) : (
                            <label className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-slate-700 rounded-xl hover:border-blue-500/50 hover:bg-slate-800/50 transition-all cursor-pointer group/upload">
                                <input type="file" className="hidden" accept="video/*" onChange={handleARollChange} />
                                <div className="w-20 h-20 rounded-full bg-slate-800 group-hover/upload:bg-blue-500/10 flex items-center justify-center transition-colors mb-4">
                                    <Upload className="w-10 h-10 text-slate-400 group-hover/upload:text-blue-400 transition-colors" />
                                </div>
                                <p className="text-slate-300 font-medium text-lg">Upload A-Roll Video</p>
                                <p className="text-slate-500 mt-2">MP4, MOV supported</p>
                            </label>
                        )}
                    </div>
                </div>

                {/* B-Roll Container */}
                <div className="group relative">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-pink-600 rounded-2xl opacity-20 group-hover:opacity-40 transition duration-500 blur"></div>
                    <div className="relative glass-card rounded-2xl p-8 h-full min-h-[400px] flex flex-col">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="p-3 bg-purple-500/10 rounded-xl">
                                <Film className="w-6 h-6 text-purple-400" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold text-slate-100">2. B-Roll Gallery</h2>
                                <p className="text-slate-500 text-sm">Supporting shots & clips</p>
                            </div>
                        </div>

                        {bRollFiles.length > 0 ? (
                            <div className="flex-1">
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                    {bRollFiles.map((file, idx) => (
                                        <div key={idx} className="relative group/item bg-slate-800 rounded-lg p-3 border border-slate-700 hover:border-purple-500/30 transition-all">
                                            <div className="aspect-video bg-slate-900 rounded flex items-center justify-center mb-2">
                                                <Film className="w-6 h-6 text-slate-600" />
                                            </div>
                                            <p className="text-xs text-slate-300 truncate">{file.name}</p>
                                            <button
                                                onClick={() => removeBRoll(idx)}
                                                className="absolute -top-1 -right-1 bg-red-500/90 text-white rounded-full p-0.5 opacity-0 group-hover/item:opacity-100 transition-opacity"
                                            >
                                                <X className="w-3 h-3" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                                <label className="flex items-center justify-center w-full py-4 border border-dashed border-slate-700 rounded-xl hover:bg-slate-800/50 hover:border-purple-500/50 cursor-pointer transition-all">
                                    <input type="file" multiple className="hidden" accept="video/*" onChange={handleBRollChange} />
                                    <span className="text-purple-400 font-medium text-sm">+ Add More Clips</span>
                                </label>
                            </div>
                        ) : (
                            <label className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-slate-700 rounded-xl hover:border-purple-500/50 hover:bg-slate-800/50 transition-all cursor-pointer group/upload">
                                <input type="file" multiple className="hidden" accept="video/*" onChange={handleBRollChange} />
                                <div className="w-20 h-20 rounded-full bg-slate-800 group-hover/upload:bg-purple-500/10 flex items-center justify-center transition-colors mb-4">
                                    <Upload className="w-10 h-10 text-slate-400 group-hover/upload:text-purple-400 transition-colors" />
                                </div>
                                <p className="text-slate-300 font-medium text-lg">Upload B-Roll Clips</p>
                                <p className="text-slate-500 mt-2">Drag & drop multiple files</p>
                            </label>
                        )}
                    </div>
                </div>
            </div>

            {/* Generate Button */}
            <div className="flex justify-center animate-slide-up" style={{ animationDelay: '0.2s' }}>
                <button
                    onClick={onGenerate}
                    disabled={!aRollFile || isGenerating}
                    className={`
            relative group px-12 py-5 rounded-full font-bold text-lg tracking-wide text-white
            ${!aRollFile || isGenerating ? 'opacity-50 cursor-not-allowed bg-slate-800' : 'cursor-pointer'}
            transition-all duration-300
          `}
                >
                    {(!aRollFile || isGenerating) ? null : (
                        <div className="absolute inset-0 rounded-full bg-gradient-to-r from-purple-600 via-violet-600 to-blue-600 blur opacity-60 group-hover:opacity-100 transition-opacity duration-300"></div>
                    )}
                    <div className={`
            relative flex items-center gap-3 bg-slate-900 rounded-full px-12 py-5 border border-white/10
            ${(!aRollFile || isGenerating) ? '' : 'bg-gradient-to-r from-purple-600 to-blue-600 border-none transform group-hover:scale-[1.02] transition-transform'}
          `}>
                        {isGenerating ? (
                            <>
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                <span>Analyzing Footage...</span>
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-5 h-5" />
                                <span>Generate Edit Plan</span>
                            </>
                        )}
                    </div>
                </button>
            </div>
        </div>
    );
}
