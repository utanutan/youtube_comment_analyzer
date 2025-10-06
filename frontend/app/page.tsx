'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api';
import { extractVideoId } from '@/lib/utils';
import AnalysisForm from '@/components/AnalysisForm';
import ResultDashboard from '@/components/ResultDashboard';

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);

  const { data: jobStatus, isLoading } = useQuery({
    queryKey: ['jobStatus', jobId],
    queryFn: () => (jobId ? apiClient.getStatus(jobId) : null),
    enabled: !!jobId,
    refetchInterval: (data: any) => {
      if (!data) return false;
      return data.status === 'queued' || data.status === 'running' ? 3000 : false;
    },
  });

  const handleSubmit = async (videoUrl: string, maxComments: number) => {
    const videoId = extractVideoId(videoUrl);
    if (!videoId) {
      alert('Invalid YouTube URL or Video ID');
      return;
    }

    try {
      const response = await apiClient.analyze({
        videoId,
        maxComments,
        lang: 'ja',
      });
      setJobId(response.jobId);
    } catch (error: any) {
      alert(`Error: ${error.response?.data?.message || error.message}`);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4">
      <div className="container mx-auto max-w-7xl">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            🎥 YouTube Comment Analyzer
          </h1>
          <p className="text-xl text-gray-600">
            AI-powered sentiment analysis for YouTube comments
          </p>
        </header>

        {!jobId ? (
          <AnalysisForm onSubmit={handleSubmit} />
        ) : (
          <ResultDashboard
            jobStatus={jobStatus}
            isLoading={isLoading}
            onReset={() => setJobId(null)}
          />
        )}
      </div>
    </main>
  );
}

