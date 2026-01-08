import { useState } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import Header from './components/Header';
import UploadSection from './components/UploadSection';
import ResultsSection from './components/ResultsSection';
import { uploadBRoll, processTimeline, pollTaskStatus } from './api/client';

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
            // 1. Upload B-Roll if exists
            if (bRollFiles.length > 0) {
                await uploadBRoll(bRollFiles, (progress) => console.log('B-Roll Upload:', progress));
            }

            // 2. Process Timeline (Upload A-Roll & Start Task)
            const { task_id } = await processTimeline(aRollFile, (progress) => console.log('A-Roll Upload:', progress));

            // 3. Poll for Completion
            const stopPolling = pollTaskStatus(task_id, (status) => {
                console.log('Task Status:', status);

                if (status.status === 'completed') {
                    // Success
                    setResults(status.result); // Assuming result matches Expected JSON format
                    setIsGenerating(false);
                    navigate('/results');
                } else if (status.status === 'failed') {
                    // Failure
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
