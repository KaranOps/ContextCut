import { useState } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import Header from './components/Header';
import { Github } from 'lucide-react';
import UploadSection from './components/UploadSection';
import ResultsSection from './components/ResultsSection';
import { uploadBRoll, processTimeline, pollTaskStatus, fetchResult } from './api/client';

function AppContent() {
    const [aRollFile, setARollFile] = useState(null);
    const [bRollFiles, setBRollFiles] = useState([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [results, setResults] = useState(null);
    const navigate = useNavigate();

    const handleARollChange = (e) => {
        const file = e.target.files[0];
        if (file) setARollFile(file);
    };

    const handleBRollChange = (e) => {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            setBRollFiles(prev => [...prev, ...files]);
        }
    };

    const removeBRoll = (index) => {
        setBRollFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleGenerate = async () => {
        if (!aRollFile) return;

        setIsGenerating(true);
        setResults(null);

        try {
            // Upload B-Roll if exists
            if (bRollFiles.length > 0) {
                await uploadBRoll(bRollFiles, (progress) => console.log('B-Roll Upload:', progress));
            }

            // Process Timeline (Upload A-Roll & Start Task)
            const { task_id } = await processTimeline(aRollFile, (progress) => console.log('A-Roll Upload:', progress));

            // Poll for Completion
            const stopPolling = pollTaskStatus(task_id, async (status) => {
                console.log('Task Status Updated:', status);

                if (status.status === 'completed') {
                    if (status.result_url) {
                        try {
                            console.log('Fetching results from:', status.result_url);
                            // Use static import now
                            const data = await fetchResult(status.result_url);
                            console.log('Fetched Data Payload:', data);

                            if (data) {
                                setResults(data);
                                setIsGenerating(false);
                                navigate('/results');
                            } else {
                                console.error('Fetched data is null/undefined!');
                                setIsGenerating(false);
                                alert('Failed to load results data (empty response).');
                            }

                        } catch (err) {
                            console.error('Failed to fetch results:', err);
                            setIsGenerating(false);
                            alert('Task completed, but failed to load results.');
                        }
                    } else {
                        console.warn('Completed but no result_url provided.');
                        setIsGenerating(false);
                        alert('Server returned no result URL.');
                    }
                } else if (status.status === 'failed') {
                    console.error('Task Failed:', status.error);
                    setIsGenerating(false);
                    alert(`Generation Failed: ${status.error}`);
                }
            });

        } catch (error) {
            console.error('Error starting generation:', error);
            setIsGenerating(false);
            alert('Failed to start generation. Check console for details.');
        }
    };

    return (
        <div className="min-h-screen p-6 md:p-12 relative">
            {/* Background Glow */}
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-900/10 rounded-full blur-[120px]"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-900/10 rounded-full blur-[120px]"></div>
            </div>

            <div className="relative max-w-7xl mx-auto space-y-12">
                <Header />

                <Routes>
                    <Route path="/" element={
                        <UploadSection
                            aRollFile={aRollFile}
                            bRollFiles={bRollFiles}
                            handleARollChange={handleARollChange}
                            handleBRollChange={handleBRollChange}
                            removeBRoll={removeBRoll}
                            onGenerate={handleGenerate}
                            isGenerating={isGenerating}
                        />
                    } />

                    <Route path="/results" element={
                        <ResultsSection results={results} />
                    } />
                </Routes>
            </div>

            {/* GitHub Link */}
            <a
                href="https://github.com/KaranOps/ContextCut"
                target="_blank"
                rel="noopener noreferrer"
                className="fixed bottom-6 right-6 p-3 bg-gray-800 text-white rounded-full shadow-lg hover:bg-gray-700 hover:scale-110 transition-all duration-300 z-50 border border-gray-700"
                title="View on GitHub"
            >
                <Github size={24} />
            </a>
        </div>
    );
}

export default function App() {
    return (
        <BrowserRouter>
            <AppContent />
        </BrowserRouter>
    );
}
